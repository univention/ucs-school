/*
 * Copyright 2012 Univention GmbH
 *
 * http://www.univention.de/
 *
 * All rights reserved.
 *
 * The source code of this program is made available
 * under the terms of the GNU Affero General Public License version 3
 * (GNU AGPL V3) as published by the Free Software Foundation.
 *
 * Binary versions of this program provided by Univention to you as
 * well as other copyrighted, protected or trademarked materials like
 * Logos, graphics, fonts, specific documentations and configurations,
 * cryptographic keys etc. are subject to a license agreement between
 * you and Univention and not subject to the GNU AGPL V3.
 *
 * In the case you use this program under the terms of the GNU AGPL V3,
 * the program is provided in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License with the Debian GNU/Linux or Univention distribution in file
 * /usr/share/common-licenses/AGPL-3; if not, see
 * <http://www.gnu.org/licenses/>.
 */
/*global define console*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dojo/_base/array",
	"dojo/topic",
	"dojo/Deferred",
	"dojo/when",
	"umc/tools",
	"umc/dialog",
	"umc/widgets/ComboBox",
	"umc/widgets/TextBox",
	"umc/widgets/Text",
	"umc/widgets/PasswordBox",
	"umc/widgets/Module",
	"umc/widgets/Wizard",
	"umc/widgets/ProgressBar",
	"umc/widgets/StandbyMixin",
	"umc/modules/lib/server",
	"umc/i18n!umc/modules/schoolinstaller"
], function(declare, lang, array, topic, Deferred, when, tools, dialog, ComboBox, TextBox, Text, PasswordBox, Module, Wizard, ProgressBar, StandbyMixin, Lib_Server, _) {

	var Installer = declare("umc.modules.schoolinstaller.Installer", [ Wizard, StandbyMixin ], {
		_initialDeferred: null,

		// entries returned from the initial request
		_serverRole: null,
		_joined: null,
		_samba: null,
		_requestRestart: false,

		_progressBar: null,

		postMixInProperties: function() {

			this.pages = [{
				name: 'setup',
				headerText: _('UCS@school - server setup'),
				helpText: _('<p>This wizard guides you step by step through the installation of UCS@school in your domain.</p><p>For the installation of UCS@school, there exist two different installation scenarios: a single master and a multi server scenario. The selection of a scenario has implications for the following installation steps. Further information for the selected scenario will be displayed below.</p>'),
				widgets: [{
					type: ComboBox,
					name: 'setup',
					label: _('Please choose an installation scenario:'),
					autoHide: true,
					sortDynamicValues: false,
					dynamicValues: lang.hitch(this, function() {
						// we can only return the setup after an intial deferred
						return this._initialDeferred.then(lang.hitch(this, function() {
							var values = [];

							// make sure we have a valid system role
							if (!this._validServerRole()) {
								return values;
							}

							// single server setup is only allowed on DC master + DC backup
							if (this._serverRole != 'domaincontroller_slave') {
								values.push({ id: 'singlemaster', label: _('Single server scenario') });
							}

							// multi server setup is allowed on all valid roles
							values.push({ id: 'multiserver', label: _('Multi server scenario') });

							return values;
						}));
					}),
					onChange: lang.hitch(this, function(newVal, widgets) {
						var texts = {
							multiserver: _('<p>In the multi server scenario, the domaincontroller master system is configured as central instance hosting the complete set of LDAP data. Each school is configured to have its own domaincontroller slave system that selectively replicates the school\'s own LDAP OU structure. In that way, different schools do not have access to data from other schools, they only see their own data. Teaching related UMC modules are only accessibly on the domaincontroller slave. The domaincontroller master does not provide UMC modules for teachers. After configuring a master system, one or more slave systems must be configured and joined into the UCS@school domain.</p>'),
							singlemaster: _('<p>In the single server scenario, the domaincontroller master system is configured as standalone UCS@school server instance. All school related data and thus all school OU structures are hosted and accessed on the domaincontroller master itself. Teaching related UMC modules are provided directly on the master itself. Note that this setup can lead to performance problems in larger environments.</p>')
						};

						// update the help text according to the value chosen...
						var text = texts[newVal] || '';

						if (this._serverRole == 'domaincontroller_slave') {
							// adaptations for text of a multi server setup on domaincontroller slaves
							text = _('<p>The local server role is domaincontroller slave, for which only a multi server setup can be configured.</p>') + text;
						}

						// update widget
						widgets.infoText.set('content', text);
					})
				}, {
					type: Text,
					name: 'infoText',
					content: ''
				}]
			}, {
				name: 'credentials',
				headerText: _('UCS@school - domain credentials'),
				helpText: _('In order to setup this system as UCS@school domaincontroller slave, please enter the domain credentials of a domain account with join privileges.'),
				widgets: [{
					type: TextBox,
					required: true,
					name: 'username',
					value: 'Administrator',
					label: _('Domain username')
				}, {
					type: PasswordBox,
					required: true,
					name: 'password',
					label: _('Domain password')
				}, {
					type: TextBox,
					required: true,
					name: 'master',
					label: _('Fully qualified domain name of domaincontroller master (e.g. schoolmaster.example.com)')
				}]
			}, {
				name: 'samba',
				headerText: _('UCS@school - samba setup'),
				helpText: _('For providing Windows domain services, UCS@school requires the installation of the Samba software component. The Samba component is available in two different versions: Samba 3 and Samba 4. It is recommended to use domain-wide the same Samba version.'),
				widgets: [{
					type: ComboBox,
					name: 'samba',
					label: _('Please choose which Samba version you would like to install:'),
					size: 'OneAndAHalf',
					staticValues: [
						{ id: '4', label: _('Active Directory-compatible domaincontroller (Samba 4)') },
						{ id: '3', label: _('NT-compatible domaincontroller (Samba 3)') }
					],
					onChange: lang.hitch(this, function(newVal, widgets) {
						var texts = {
							'samba4': _('Samba 4 provides full Active Directory (AD) functionality. A Sama 4 server can act as AD Domain Controller for Windows systems.'),
							'samba3': _('Samba 3 can only provide Domain Controller functionality for a Windows NT network domain. A Samba 3 system cannot provide Domain Controller functionality for an Active Directory (AD) domain, however, it can be member of an AD domain.')
						};

						// update the help text according to the value chosen...
						var text = texts['samba' + newVal];

						// update widget
						widgets.infoText.set('content', text);
					})
				}, {
					type: Text,
					name: 'infoText',
					content: ''
				}]
			}, {
				name: 'school',
				headerText: _('UCS@school - school OU setup'),
				helpText: _('In UCS@school, each school is organized in its proper LDAP organizational unit (so-called OU). All school related information (students, classes, computers, rooms, groups etc.) is organized below such an OU. Please enter the name of a school OU that will be created during the installation process.'),
				widgets: [{
					type: TextBox,
					required: true,
					name: 'schoolOU',
					label: _('School OU name'),
					regExp: '^[a-zA-Z0-9](([a-zA-Z0-9_]*)([a-zA-Z0-9]$))?$'
				}, {
					// this information will only be shown to slave systems
					type: Text,
					name: 'infoTextSlave',
					content: '<p>' + _('Note that each domaincontroller slave system is directly associated with its proper school OU. A domaincontroller slave has only access to the data below its own school OU, not to data from other schools.') + '</p>'
				}, {
					// this information will only be shown to master systems in the singlemaster setup
					type: Text,
					name: 'infoTextMaster',
					content: '<p>' + _('For the single server scenario, all school OUs are accessed from the master system itself.') + '</p>'
				}]
			}, {
				name: 'error',
				headerText: _('UCS@school - an error ocurred'),
				helpText: _('An error occurred during the installation of UCS@school. The following information will give you some more details on which problems occurred during the installation process.'),
				widgets: [{
					type: Text,
					name: 'info',
					style: 'font-style:italic;',
					content: ''
				}]
			}, {
				name: 'success',
				headerText: _('UCS@school - installation successful'),
				helpText: _('The installation of UCS@school has been finished successfully.'),
				widgets: [{
					type: Text,
					name: 'info',
					content: ''
				}]
			}, {
				name: 'alreadyInstalled',
				headerText: _('UCS@school installation wizard'),
				helpText: _('UCS@school has already been configured on this system.')
			}];

			this.inherited(arguments);
		},

		buildRendering: function() {
			this.inherited(arguments);

			// initiate a progress bar widget
			this._progressBar = new ProgressBar();
			this.own(this._progressBar);

			// change labels of default footer buttons
//			this._pages.school._footerButtons.next.set('label', _('Install'));
			this._pages.error._footerButtons.next.set('label', _('Retry'));
			this._pages.alreadyInstalled._footerButtons.finish.set('label', _('Close'));

			// initial query for server details
			this._initialQuery();
		},

		_initialQuery: function() {
			// initial standby animation
			this.standby(true);

			// query initial information
			this._initialDeferred = tools.umcpCommand('schoolinstaller/query').then(lang.hitch(this, function(data) {
				this._serverRole = data.result.server_role;
				this._joined = data.result.joined;
				this._samba = data.result.samba;
				this._ucsschool = data.result.ucsschool;
				var guessedMaster = data.result.guessed_master;

				// update some widgets with the intial results
				if (this._samba) {
					this.getWidget('samba', 'samba').set('value', this._samba);
				}
				this.getWidget('credentials', 'master').set('value', guessedMaster);

				// switch off standby animation
				this.standby(false);
			}), lang.hitch(this, function() {
				// switch off standby animation
				this.standby(false);
			}));
		},

		_installationFinished: function(deferred) {
			// get all error information and decide which next page to display
			var info = this._progressBar.getErrors();
			var nextPage = info.errors.length ? 'error' : 'success';

			if (info.errors.length == 1) {
				// one error can be displayed as text
				this.getWidget(nextPage, 'info').set('content', info.errors[0]);
			}
			else if (info.errors.length > 1) {
				// display multiple errors as unordered list
				var html = '<ul>';
				array.forEach(info.errors, function(txt) {
					html += lang.replace('<li>{0}</li>\n', [txt]);
				});
				html += '</ul>';
				this.getWidget(nextPage, 'info').set('content', html);
			}
			else {
				// no errors... we need a UMC server restart
				this._requestRestart = true;
			}

			if (deferred) {
				// finish the deferred object to indicate the next page
				deferred.resolve(nextPage);
			}
		},

		next: function(pageName) {
			var next = this.inherited(arguments);

			if (!pageName) {
				// enforce an button update in the beginning to avoid all buttons being visible
				this._updateButtons('setup');
			}

			// if we retry from the error page, resend the intial query
			if (pageName == 'error') {
				this._initialQuery();
			}

			return this._initialDeferred.then(lang.hitch(this, function() {
				// block invalid server roles
				if (!this._validServerRole()) {
					dialog.alert(_('UCS@school can only be installed on the system roles domaincontroller master, domaincontroller backup, or domaincontroller slave.'));
					return 'setup';
				}

				// check whether UCS@school has already been installed on the system
				if (this._ucsschool) {
					return 'alreadyInstalled';
				}

				// make sure that all form elements are filled out correctly
				if (pageName && !this.getPage(pageName)._form.validate()) {
					return pageName;
				}

				// retry when an error occurred
				if (pageName == 'error') {
					next = 'credentials';
				}

				// show credentials page only on domaincontroller Slave
				if (next == 'credentials' && this._serverRole != 'domaincontroller_slave') {
					next = 'samba';
				}

				// only display samba page for a single master setup or on a
				// slave and only if samba is not already installed
				if (next == 'samba' && (this._samba || (this.getWidget('setup', 'setup').get('value') == 'multiserver' && this._serverRole != 'domaincontroller_slave'))) {
					next = 'school';
				}

				// installation
				if (pageName == 'school' || (next == 'school' && this.getWidget('setup', 'setup').get('value') == 'multiserver' && this._serverRole == 'domaincontroller_master')) {
					// start standby animation
					var values = this.getValues();

					// clear entered password and make sure that no error is indicated
					this.getWidget('credentials', 'password').set('value', '');
					this.getWidget('credentials', 'password').set('state', 'Incomplete');

					// request installation
					next = dialog.confirm(_('Please confirm to start the installation process.'), [{
						name: 'install',
						label: _('Install')
					}, {
						name: 'cancel',
						label: _('Cancel'),
						'default': true
					}]).then(lang.hitch(this, function(install) {
						if (install == 'cancel') {
							return pageName;
						}
						this.standby(true);
						return tools.umcpCommand('schoolinstaller/install', values).then(lang.hitch(this, function(result) {
							if (!result.result.success) {
								this.getWidget('error', 'info').set('content', result.result.error);
								return 'error';
							}

							// show the progress bar
							this._progressBar.reset(_('Starting the configuration process...' ));
							this.standby(true, this._progressBar);
							var deferred = new Deferred();
							this._progressBar.auto(
								'schoolinstaller/progress',
								{},
								lang.hitch(this, '_installationFinished', deferred),
								undefined,
								undefined,
								true
							);
							return deferred;
						}), lang.hitch(this, function(error) {
							// an unexpected error occurred
							this.getWidget('error', 'info').set('content', _('An unexpected error occurred.'));
							return 'error';
						}));
					}));

					next.then(lang.hitch(this, function() {
						this.standby(false);
					}));
				}

				when(next, lang.hitch(this, function(next) {
					// call the corresponding update method of the next page
					if (this['_update_' + next + '_page']) {
						var updateFunc = lang.hitch(this, '_update_' + next + '_page');
						updateFunc();
					}
				}));

				return next;
			}));
		},

		_update_school_page: function() {
			var values = this.getValues();
			this.getWidget('school', 'infoTextMaster').set('visible', this._serverRole != 'domaincontroller_slave' && values.setup == 'singlemaster');
			this.getWidget('school', 'infoTextSlave').set('visible', this._serverRole == 'domaincontroller_slave');
		},

		_update_success_page: function() {
			if (this._requestRestart) {
				// prompt an information for UMC restart
				var msg = _('For all changes to take effect, a restart of the UMC server components is necessary after the domain join.');
				Lib_Server.askRestart(msg);
			}
		},

		canCancel: function(pageName) {
			return pageName != 'success' && pageName != 'alreadyInstalled';
		},

		hasNext: function(pageName) {
			return pageName != 'success' && pageName != 'alreadyInstalled';
		},

		hasPrevious: function(pageName) {
			return this.inherited(arguments) && pageName != 'error' && pageName != 'success' && pageName != 'alreadyInstalled';
		},

		previous: function(pageName) {
			var previous = this.inherited(arguments);

			// only display samba page for a single master setup or on a
			// slave and only if samba is not already installed
			if (previous == 'samba' && (this._samba || (this.getWidget('setup', 'setup').get('value') == 'multiserver' && this._serverRole != 'domaincontroller_slave'))) {
				previous = 'credentials';
			}

			// show credentials page only on DC Slave
			if (previous == 'credentials' && this._serverRole != 'domaincontroller_slave') {
				previous = 'setup';
			} else if (previous == 'error') {
				previous = 'school';
			}

			return previous;
		},

		// only DC master, DC backup, and DC slave are valid system roles for this module
		_validServerRole: function() {
			return this._serverRole == 'domaincontroller_master' || this._serverRole == 'domaincontroller_backup' || this._serverRole == 'domaincontroller_slave';
		}

	});

	return declare("umc.modules.schoolinstaller", [ Module ], {
		// internal reference to the installer
		_installer: null,

		buildRendering: function() {
			this.inherited(arguments);

			this._installer = new Installer({});
			this.addChild(this._installer);

			this._installer.on('finished', lang.hitch(this, function() {
				topic.publish('/umc/tabs/close', this);
			}));
			this._installer.on('cancel', lang.hitch(this, function() {
				topic.publish('/umc/tabs/close', this);
			}));
		}
	});
});
