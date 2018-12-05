/*
 * Copyright 2012-2018 Univention GmbH
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
/*global define*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dojo/_base/array",
	"dojo/topic",
	"dojo/Deferred",
	"dojo/when",
	"dojox/html/entities",
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
], function(declare, lang, array, topic, Deferred, when, entities, tools, dialog, ComboBox, TextBox, Text, PasswordBox, Module, Wizard, ProgressBar, StandbyMixin, Lib_Server, _) {

	var Installer = declare("umc.modules.schoolinstaller.Installer", [ Wizard, StandbyMixin ], {
		_initialDeferred: null,
		installationLock: null,

		// entries returned from the initial request
		_serverRole: null,
		_joined: null,
		_requestRestart: false,
		_hostname: null,

		_progressBar: null,

		postMixInProperties: function() {

			this.pages = [{
				name: 'setup',
				headerText: _('UCS@school - server setup'),
				helpText: _('<p>This wizard guides you step by step through the installation of UCS@school in your domain.</p><p>For the installation of UCS@school, there exist two different environment types: the single server environment and the multi server environment. The selection of an environment type has implications for the following installation steps. Further information for the selected environment type will be displayed below.</p>') + _('<p>During the installation of UCS@school a demo school including some users and a portal will be configured for testing purposes. If you do not wish that, please set the UCR variable <emp>ucsschool/join/create_demo</emp> to <emp>no</emp> prior to the installation.</p>'),
				widgets: [{
					type: ComboBox,
					name: 'setup',
					label: _('Please choose an environment type:'),
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

							// single server environment is only allowed on DC master + DC backup
							if (this._serverRole !== 'domaincontroller_slave') {
								values.push({ id: 'singlemaster', label: _('Single server environment') });
							}

							// multi server environment is allowed on all valid roles
							values.push({ id: 'multiserver', label: _('Multi server environment') });

							return values;
						}));
					}),
					onChange: lang.hitch(this, function(newVal, widgets) {
						var texts = {
							multiserver: _('<p>In a multi server environment, the master domain controller system is configured as central instance hosting the complete set of LDAP data. Each school is configured to have its own slave domain controller system that selectively replicates the school\'s own LDAP OU structure. In that way, different schools do not have access to data from other schools, they only see their own data. Teaching related UMC modules are only accessible on the slave domain controller. The master domain controller does not provide UMC modules for teachers. After configuring a master system, one or more slave systems must be configured and joined into the UCS@school domain.</p>'),
							singlemaster: _('<p>In a single server environment, the master domain controller system is configured as standalone UCS@school server instance. All school related data and thus all school OU structures are hosted and accessed on the master domain controller itself. Teaching related UMC modules are provided directly on the master itself. Note that this setup can lead to performance problems in larger environments.</p>')
						};

						// update the help text according to the value chosen...
						var text = texts[newVal] || '';

						if (this._serverRole === 'domaincontroller_slave') {
							// adaptations for text of a multi server environment on slave domain controllers
							//text = _('<p>The local server role is slave domain controller, for which only a multi server environment can be configured.</p>') + text;
							text = '';
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
				name: 'backupsetup',
				headerText: _('UCS@school - server setup'),
				widgets: [{
					type: Text,
					name: 'backup_text',
					content: _('The UCS@school configuration wizard detected all necessary information to install UCS@school on this DC Backup. Click <i>next</i> to start the installation.')
				}]
			}, {
				name: 'credentials',
				headerText: _('UCS@school - domain credentials'),
				helpText: _('In order to setup this system as UCS@school slave domain controller, please enter the domain credentials of a domain account with join privileges.'),
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
					regExp: '^[a-z]([a-z0-9-]*[a-z0-9])*(\\.([a-z0-9]([a-z0-9-]*[a-z0-9])*[.])*[a-z0-9]([a-z0-9-]*[a-z0-9])*)?$', // see __init__.py RE_HOSTNAME
					name: 'master',
					label: _('Fully qualified domain name of master domain controller (e.g. schoolmaster.example.com)')
				}, {
					type: Text,
					name: 'dnsLookupError',
					content: '',
					visible: false
				}]
			}, {
				name: 'school',
				headerText: _('UCS@school - school OU setup'),
				helpText: _('In UCS@school, each school is organized in its own LDAP organizational unit (so-called OU). All school related information (students, classes, computers, rooms, groups etc.) is organized below such an OU. Please enter the name of a school OU that will be created during the installation process.'),
				widgets: [{
					type: TextBox,
					name: 'OUdisplayname',
					label: _('Name of the school'),
					description: _('The given value will be shown as school\'s name within UCS@school.'),
					required: true
				}, {
					type: TextBox,
					name: 'schoolOU',
					label: _("School abbreviation"),
					description: _('The given value will be used as object name for the new school OU object within the LDAP directory and as prefix for several school objects like group names. It may consist of the letters a-z, the digits 0-9 and underscores. Usually it is safe to keep the suggested value.'),
					regExp: '^[a-zA-Z0-9](([a-zA-Z0-9_]*)([a-zA-Z0-9]$))?$',
					depends: ['OUdisplayname'],
					dynamicValue: function(values) { return values.OUdisplayname.replace(/[^a-zA-Z0-9]/g, ''); },
					required: true
				}, {
					// this information will only be shown to slave systems
					type: Text,
					name: 'infoTextSlave',
					content: '<p>' + _('Note that each slave domain controller system is directly associated with a school OU. A slave domain controller has only access to the data below its own school OU, not to data from other schools.') + '</p>'
				}, {
					// this information will only be shown to master systems in the single server environment
					type: Text,
					name: 'infoTextMaster',
					content: '<p>' + _('For the single server environment, all school OUs are accessed from the master system itself.') + '</p>'
				}]
			}, {
				name: 'server_type',
				headerText: _('UCS@school - educational server vs. administrative server'),
				helpText: _('<p>The UCS@school multi server environment distinguishes between educational servers and administrative servers. The educational servers provide all educational functions of UCS@school. The administrative servers only provide a very limited set of functions, e.g. logon services for staff users.</p><p>Usually the domain controller slave is configured as educational server.</p>'),
				widgets: [{
					type: ComboBox,
					name: 'server_type',
					label: _('Please choose the server type for this domain controller slave:'),
					staticValues: [
						{ id: 'educational', label: _('Educational server') },
						{ id: 'administrative', label: _('Administrative server') }
					]
				}]
			}, {
				name: 'administrativesetup',
				headerText: _('UCS@school - extended school OU setup'),
				helpText: _('During installation this server will be configured as administrative server. To create the specified school, the name of a second/future domain controller slave is required, which will be configured as educational server.'),
				widgets: [{
					type: TextBox,
					name: 'nameEduServer',
					label: _("Name of educational school server"),
					description: _('Name of the educational domain controller slave for the new school. The server name may consist of the letters a-z, the digits 0-9 and hyphens (-). The name of the educational server may not be equal to the administrative server!'),
					regExp: '^[a-zA-Z0-9](([a-zA-Z0-9-]*)([a-zA-Z0-9]$))?$',
					required: true
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
				helpText: _('UCS@school has already been configured on this system.'),
				widgets: [{
					type: Text,
					name: 'info',
					content: (function() {
						var classLink = tools.linkToModule({module: 'schoolwizards', flavor: 'schoolwizards/classes'});
						var userLink = tools.linkToModule({module: 'schoolwizards', flavor: 'schoolwizards/users'});
						var groupLink = tools.linkToModule({module: 'schoolgroups', flavor: 'class'});
						var workgroupLink = tools.linkToModule({module: 'schoolgroups', flavor: 'workgroup-admin'});

						if (!(classLink || userLink || groupLink || workgroupLink)) {
							return '';
						}
						var content = _('There are several modules that assist in further configuring the UCS@school domain:') + '<ul>';
						if (classLink) {
							content += '<li>' + _('New school classes can be created with the %s.', classLink) + '</li>';
						}
						if (userLink) {
							content += '<li>' + _('Teachers and students can be added to the UCS@school domain with the %s.', userLink) + '</li>';
						}
						if (groupLink) {
							content += '<li>' + _('Teachers can be assigned to classes with the %s.', groupLink) + '</li>';
						}
						if (workgroupLink) {
							content += '<li>' + _('Workgroups can be created and managed with the %s.', workgroupLink) + '</li>';
						}
						content += '</ul>';
						return content;
					})()
				}]
			}];

			this.inherited(arguments);

			this.standbyOpacity = 1;
		},

		buildRendering: function() {
			this.inherited(arguments);

			// initiate a progress bar widget
			this._progressBar = new ProgressBar();
			this.own(this._progressBar);

			// change labels of default footer buttons
//			this._pages.school._footerButtons.next.set('label', _('Install'));
			this._pages.error._footerButtons.next.set('label', _('Retry'));

			// initial query for server details
			this._initialQuery();
		},

		_initialQuery: function() {
			// query initial information
			this._initialDeferred = this.standbyDuring(tools.umcpCommand('schoolinstaller/query').then(lang.hitch(this, function(data) {
				this._serverRole = data.result.server_role;
				this._hostname = data.result.hostname;
				this._joined = data.result.joined;
				this._ucsschool = data.result.school_environment;
				var guessedMaster = data.result.guessed_master;

				// update some widgets with the intial results
				if (this._serverRole === 'domaincontroller_slave') {
					this._pages.setup.set('helpText', _('This wizard guides you step by step through the installation of an UCS@school slave domain controller. Before continuing please make sure that an UCS@school master domain controller has already been set up for a multi server environment.'));
				}
				this.getWidget('credentials', 'master').set('value', guessedMaster);
				if (!guessedMaster) {
					var networkLink = tools.linkToModule({module: 'setup', flavor: 'network'});
					var widget = this.getWidget('credentials', 'dnsLookupError');
					var _warningMessage = lang.replace('<b>{0}</b> {1} {2} {3}', [
						_('Warning:'),
						_('Could not find the DNS entry for the domain controller master.'),
						_('Make sure the DNS server is up and running or check the DNS settings.'),
						networkLink ? _('The DNS settings can be adjusted in the %s.', networkLink) : ''
					]);
					widget.set('content', _warningMessage);
					widget.set('visible', true);
				}
			})));
		},

		getSchoolInfo: function() {
			var args = {
				school: this.getWidget('school', 'schoolOU').get('value'),
				username: this.getWidget('credentials', 'username').get('value'),
				password: this.getWidget('credentials', 'password').get('value'),
				master: this.getWidget('credentials', 'master').get('value')
			};
			return tools.umcpCommand('schoolinstaller/get/schoolinfo', args);
		},

		_installationFinished: function(deferred) {
			// get all error information and decide which next page to display
			var info = this._progressBar.getErrors();
			var nextPage = info.errors.length ? 'error' : 'success';

			if (info.errors.length === 1) {
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
			if (pageName === 'error') {
				this._initialQuery();
			}

			return this._initialDeferred.then(lang.hitch(this, function() {
				// block invalid server roles
				if (!this._validServerRole()) {
					dialog.alert(_('UCS@school can only be installed on the system roles master domain controller, backup domain controller, or slave domain controller.'));
					return 'setup';
				}

				// a DC backup needs to be joined
				if (this._serverRole === 'domaincontroller_backup' && !this._joined) {
					dialog.alert(_('In order to install UCS@school on a backup domain controller, the system needs to be joined first.'));
					return 'setup';
				}

				// check whether UCS@school has already been installed on the system
				if (this._ucsschool) {
					return 'alreadyInstalled';
				}

				// make sure that all form elements are filled out correctly
				if (pageName && this.getPage(pageName)._form && !this.getPage(pageName)._form.validate()) {
					return pageName;
				}

				// retry when an error occurred
				if (pageName === 'error') {
					next = 'setup';
				}

				// domaincontroller backup can start directly
				if (next === 'setup' && this._serverRole === 'domaincontroller_backup') {
					return this.standbyDuring(tools.umcpCommand('schoolinstaller/get/metainfo').then(lang.hitch(this, function(data) {
						var metainfo = data.result;
						if (!metainfo) {
							return 'credentials';  // the DC Backup is not joined yet/anymore. Continue with the next page. Cannot happen as UCS@school is now installed via the AppCenter so the system must be joined.
						}
						this.getWidget('setup', 'setup').set('value', metainfo.school_environment);
						return 'backupsetup';
					})));
				}

				if (next === 'backupsetup' && this._serverRole !== 'domaincontroller_backup') {
					next = 'credentials';
				}

				// show credentials page only on domaincontroller slave
				if (next === 'credentials' && this._serverRole !== 'domaincontroller_slave') {
					next = 'school';
				}

				// no schoolOU/server_type/administrativesetup page on a DC master w/multi server environment and a DC backup in general
				if (next === 'school' && ((this.getWidget('setup', 'setup').get('value') === 'multiserver' && this._serverRole === 'domaincontroller_master') || this._serverRole === 'domaincontroller_backup')) {
					next = 'install';
				}

				// show server type page only on domaincontroller slave
				if (next === 'server_type' && this._serverRole !== 'domaincontroller_slave') {
					next = 'install';
				}

				// show managementsetup page only if no slave has been specified or OU does not exist yet
				if (next === 'administrativesetup') {
					next = this.standbyDuring(this.getSchoolInfo()).then(lang.hitch(this, function(data) {
						var schoolinfo = data.result;

						if (this.getWidget('server_type', 'server_type').get('value') === 'educational') {
							// check if there are other UCS@school slaves defined
							if ((schoolinfo.educational_slaves.length > 0) && (array.indexOf(schoolinfo.educational_slaves, this._hostname) < 0)) {
								// show error message and then jump back to server role selection
								return dialog.confirm('<div style="max-width: 500px">' + _('UCS@school supports only one educational server per school. Please check if the educational server "') + schoolinfo.educational_slaves[0] + _('" is still in use. Otherwise the corresponding host object has to be deleted first.') + '</div>', [{
									name: 'ok',
									label: _('Ok'),
									'default': true
								}], _('Error')).then(lang.hitch(this, function() {
									return 'server_type';
								}));
							} else {
								// otherwise start installation
								return this._start_installation(pageName);
							}
						} else {
							// check if there are other UCS@school slaves defined
							if ((schoolinfo.administrative_slaves.length > 0) && (array.indexOf(schoolinfo.administrative_slaves, this._hostname) < 0)) {
								// show error message and then jump back to server role selection
								return dialog.confirm('<div style="max-width: 500px">' + _('UCS@school supports only one administrative server per school. Please check if the administrative server "') + schoolinfo.administrative_slaves[0] + _('" is still in use. Otherwise the corresponding host object has to be deleted first.') + '</div>', [{
									name: 'ok',
									label: _('Ok'),
									'default': true
								}], _('Error')).then(lang.hitch(this, function() {
									return 'server_type';
								}));
							} else  {
								// otherwise ask for a name of the educational slave if none is already define; if defined, start the installation
								if (schoolinfo.educational_slaves.length > 0) {
									this.getWidget('administrativesetup', 'nameEduServer').set('value', schoolinfo.educational_slaves[0]);
									return this._start_installation(pageName); // Warning: the deferred object returns a deferred object!
								} else {
									return 'administrativesetup';
								}
							}
						}
					}));
				}

				// after the administrativesetup page, the installation begins
				if (pageName === 'administrativesetup') {
					next = 'install';
				}

				if (pageName === 'backupsetup') {
					next = 'install';
				}

				// installation
				if (next === 'install') {
					next = this._start_installation(pageName);
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

		_start_installation: function(pageName) {
			var values = this.getValues();
			if (this.installationLock && !this.installationLock.isFulfilled()) {
				console.error('The installation is already running. Cannot do parallel installations.');
				throw 'The installation is already running. Cannot do parallel installations.';
			}

			// request installation
			var next = dialog.confirm('<div style="max-width: 500px">' + _('All necessary information for the installation of UCS@school on this system has been collected. It is recommended to wait with any other activity on the system until the installation has been completed. Please confirm now to continue with the installation process.') + '</div>', [{
				name: 'cancel',
				label: _('Cancel'),
				'default': true
			}, {
				name: 'install',
				label: _('Install')
			}]).then(lang.hitch(this, function(install) {
				if (install === 'cancel') {
					return pageName;
				}

				// show the progress bar
				this._progressBar.reset(_('Starting the configuration process...' ));
				this._progressBar._progressBar.set('value', Infinity); // TODO: Remove when this is done automatically by .reset()
				this.standbyDuring(next, this._progressBar);

				// clear entered password and make sure that no error is indicated
				this.getWidget('credentials', 'password').set('value', '');
				this.getWidget('credentials', 'password').set('state', 'Incomplete');

				return tools.umcpCommand('schoolinstaller/install', values).then(lang.hitch(this, function() {
					this._progressBar.setInfo(null, null, 0); // 0%
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
					this.getWidget('error', 'info').set('content', entities.encode(tools.parseError(error).message));
					return 'error';
				}));
			}));

			this.installationLock = next;

			return next;
		},

		_update_school_page: function() {
			var values = this.getValues();
			this.getWidget('school', 'infoTextMaster').set('visible', this._serverRole !== 'domaincontroller_slave' && values.setup === 'singlemaster');
			this.getWidget('school', 'infoTextSlave').set('visible', this._serverRole === 'domaincontroller_slave');
		},

		_update_success_page: function() {
			if (this._requestRestart) {
				// prompt an information for UMC restart
				var msg = _('In order to complete the installation of UCS@school, a restart of the UMC server components is necessary.');
				Lib_Server.askRestart(msg);
			}
		},

		canCancel: function(pageName) {
			// deactivate this, because the wizard can be closed via the header
			// button anyways
			return false;
		},

		getFooterButtons: function(pageName) {
			var buttons = this.inherited(arguments);
			if (pageName === 'alreadyInstalled') {
				buttons = array.filter(buttons, function(button) { return button.name !== 'finish'; });
			}
			return buttons;
		},

		hasNext: function(pageName) {
			return pageName !== 'success' && pageName !== 'alreadyInstalled';
		},

		hasPrevious: function(pageName) {
			return this.inherited(arguments) && pageName !== 'error' && pageName !== 'success' && pageName !== 'alreadyInstalled' && pageName !== 'backupsetup';
		},

		previous: function(pageName) {
			var previous = this.inherited(arguments);

			// DC Master/Slave doesn't have the backup page
			if (previous === 'backupsetup') {
				previous = 'setup';
			}

			// show credentials page only on DC Slave
			if (previous === 'credentials' && this._serverRole !== 'domaincontroller_slave') {
				previous = 'setup';
			} else if (previous === 'error') {
				previous = 'school';
			}

			return previous;
		},

		// only DC master, DC backup, and DC slave are valid system roles for this module
		_validServerRole: function() {
			return this._serverRole === 'domaincontroller_master' || this._serverRole === 'domaincontroller_backup' || this._serverRole === 'domaincontroller_slave';
		}

	});

	return declare("umc.modules.schoolinstaller", [ Module ], {
		// internal reference to the installer
		_installer: null,

		unique: true, // only one UCS@school installer may be opened at the same time

		buildRendering: function() {
			this.inherited(arguments);

			this._installer = new Installer({ 'class': 'umcCard' });
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
