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
	"umc/i18n!umc/modules/schoolinstaller"
], function(declare, lang, array, topic, Deferred, tools, dialog, ComboBox, TextBox, Text, PasswordBox, Module, Wizard, ProgressBar, StandbyMixin, _) {

	var Installer = declare("umc.modules.schoolinstaller.Installer", [ Wizard, StandbyMixin ], {
		_initialDeferred: null,

		// entries returned from the initial request
		_serverRole: null,
		_joined: null,
		_samba: null,

		_progressBar: null,

		postMixInProperties: function() {

			this.pages = [{
				name: 'setup',
				headerText: _('UCS@school - server setup'),
				helpText: _('This wizard guides you step by step through the installation of UCS@school in your domain...'),
				widgets: [{
					type: ComboBox,
					name: 'setup',
					label: _('Domain setup'),
					autoHide: true,
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
								values.push({ id: 'singlemaster', label: _('Single server setup') });
							}

							// multi sever setup is allowed on all valid roles
							values.push({ id: 'multiserver', label: _('Multi server setup') });

							return values;
						}));
					}),
					onChange: lang.hitch(this, function(newVal, widgets) {
						var texts = {
							multiserver: _('<p>In the multi server setup, the DC master system is configured as central instance hosting the complete set of LDAP data. Each school is configured to have its own DC slave system that selectively replicates the school\'s own LDAP OU structure. In that way, different schools do not have access to data from other schools, they only see their own data.</p>'),
							singlemaster: _('<p>In the single server setup, the DC master system is configured as standalone UCS@school server instance. All school related data and thus all school OU structures are hosted and accessed on the DC master itself.</p>')
						};

						// update the help text according to the value chosen...
						var text = texts[newVal];

						if (this._serverRole == 'domaincontroller_slave') {
							// adaptations for text of a multi server setup on DC slaves
							text = _('<p>The local server role is DC slave, for which only a multi server setup can be configured.</p>') + text;
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
				headerText: _('UCS@school - Domain credentials (only Slave)'),
				helpText: _('In order to setup this system as UCS@school DC slave, please enter the domain credentials of a domain account with administrator privilgeges.'),
				widgets: [{
					type: TextBox,
					required: true,
					name: 'username',
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
					label: _('Domain DC master system (e.g., schoolmaster.example.com)')
				}]
			}, {
				name: 'samba',
				headerText: _('UCS@school - Samba setup'),
				helpText: _('For Windows domain services, UCS@school needs the installation of the Samba software component. Please choose which Samba version you would like to install.'),
				widgets: [{
					type: ComboBox,
					name: 'samba',
					label: _('Samba setup'),
					staticValues: [
						{ id: 4, label: _('Active Directory-compatible domaincontroller (Samba 4)') },
						{ id: 3, label: _('NT-compatible domaincontroller (Samba 3)') }
					],
					onChange: lang.hitch(this, function(newVal, widgets) {
						var texts = {
							'samba4': _('More details to Samba 4...'),
							'samba3': _('More details to Samba 3...')
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
				helpText: _('Please enter the name of the first school OU... (explain what a school OU is for and how the structure is).'),
				widgets: [{
					type: TextBox,
					required: true,
					name: 'schoolOU',
					label: _('School OU name'),
					regExp: '^[a-zA-Z0-9](([a-zA-Z0-9_]*)([a-zA-Z0-9]$))?$'
				}]
			}, {
				name: 'error',
				headerText: _('UCS@school - installation failed'),
				helpText: _('The installation of UCS@school failed.'),
				widgets: [{
					type: Text,
					name: 'info',
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
			this._pages.school._footerButtons.next.set('label', _('Install'));
			this._pages.error._footerButtons.next.set('label', _('Retry'));

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
				guessedMaster = data.result.guessed_master;

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

			if (deferred) {
				// finish the deferred object to indicate the next page
				deferred.resolve(nextPage);
			}
		},

		next: function(pageName) {
			var next = this.inherited(arguments);

			// if we retry from the error page, resend the intial query
			if (pageName == 'error') {
				this._initialQuery();
			}

			return this._initialDeferred.then(lang.hitch(this, function() {
				// block invalid server roles
				if (!this._validServerRole()) {
					dialog.alert(_('UCS@school can only be installed on the system roles DC master, DC backup, or DC slave.'));
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

				// show credentials page only on DC Slave
				if (next == 'credentials' && this._serverRole != 'domaincontroller_slave') {
					next = 'samba';
				}

				// only display samba page for a single master setup or on a
				// slave and only if samba is not already installed
				if (next == 'samba' && (this._samba || (this.getWidget('setup', 'setup').get('value') == 'multiserver' && this._serverRole != 'domaincontroller_slave'))) {
					next = 'school';
				}

				// installation
				if (pageName === 'school') {
					// start standby animation
					this.standby(true);
					var values = this.getValues();

					// clear entered password and make sure that no error is indicated
					this.getWidget('credentials', 'password').set('value', '');
					this.getWidget('credentials', 'password').set('state', 'Incomplete');

					// request installation
					var deferred = new Deferred();
					tools.umcpCommand('schoolinstaller/install', values).then(lang.hitch(this, function(result) {
						this.standby(false);

						if (!result.result.success) {
							this.getWidget('error', 'info').set('content', result.result.error);
							deferred.resolve('error');
							return;
						}

						// show the progress bar
						this._progressBar.reset(_('Starting the configuration process...' ));
						this.standby(true, this._progressBar);
						this._progressBar.auto(
							'schoolinstaller/progress',
							{},
							lang.hitch(this, '_installationFinished', deferred),
							undefined,
							undefined,
							true
						);
					}), lang.hitch(this, function(error) {
						// an unexpected error occurred
						this.standby(false);
						this.getWidget('error', 'info').set('content', _('An unexpected error occurred.'));
						deferred.resolve('error');
					}));

					// stop standby animation when finished
					deferred.then(lang.hitch(this, function() {
						this.standby(false);
					}));

					return deferred;
				}

				// call the corresponding update method of the next page
				/*if (this['_update_' + next + '_page']) {
					var updateFunc = lang.hitch(this, '_update_' + next + '_page');
					updateFunc();
				}*/

				return next;
			}));
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
			// FIXME: dont go back to samba if samba is installed

			// show credentials page only on DC Slave
			if (previous === 'credentials' && this._serverRole != 'domaincontroller_slave') {
				previous = 'setup';
			} else if (previous === 'error') {
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
