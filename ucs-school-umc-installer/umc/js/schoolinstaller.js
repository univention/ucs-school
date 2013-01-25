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
/*global define*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dojo/topic",
	"umc/tools",
	"umc/dialog",
	"umc/widgets/ComboBox",
	"umc/widgets/TextBox",
	"umc/widgets/PasswordBox",
	"umc/widgets/Module",
	"umc/widgets/Wizard",
	"umc/widgets/StandbyMixin",
	"umc/i18n!umc/modules/schoolinstaller"
], function(declare, lang, topic, tools, dialog, ComboBox, TextBox, PasswordBox, Module, Wizard, StandbyMixin, _) {
	var Installer = declare("umc.modules.schoolinstaller.Installer", [ Wizard, StandbyMixin ], {
		_initialDeferred: null,
		_serverRole: null,
		_joined: null,

		postMixInProperties: function() {

			this.pages = [{
				name: 'setup',
				headerText: _('UCS@school - server setup'),
				helpText: _('This wizard guides you step by step through the installation of UCS@school in your domain...'),
				widgets: [{
					type: ComboBox,
					name: 'setup',
					label: _('Domain setup'),
					staticValues: [
						{ id: 'singleserver', label: _('Single server setup') },
						{ id: 'multiserver', label: _('Multi server setup') }
					]
				}]
			}, {
				name: 'credentials',
				headerText: _('UCS@school - Domain credentials (only Slave)'),
				helpText: _('In order to setup this system as UCS@school DC slave, please enter the domain credentials of a domain account with administrator privilgeges.'),
				widgets: [{
					type: TextBox,
					name: 'username',
					label: _('Domain username')
				}, {
					type: PasswordBox,
					name: 'password',
					label: _('Domain password')
				}, {
					type: TextBox,
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
						{ id: 'samba4', label: _('Samba4') },
						{ id: 'samba', label: _('Samba3') }
					]
				}]
			}, {
				name: 'school',
				headerText: _('UCS@school - school OU setup'),
				helpText: _('Please enter the name of the first school OU... (explain what a school OU is for and how the structure is).'),
				widgets: [{
					type: TextBox,
					name: 'schoolOU',
					label: _('School OU name')
				}]
			}, {
				name: 'error',
				headerText: _('UCS@school - installation failed'),
				helpText: _('The installation of UCS@school failed.')
			}, {
				name: 'done',
				headerText: _('UCS@school - installation successful'),
				helpText: _('The installation of UCS@school has been finised successfully.')
			}];

			this.inherited(arguments);
		},

		buildRendering: function() {
			this.inherited(arguments);

			// query initial information
			this._initialDeferred = tools.umcpCommand('schoolinstaller/query').then(lang.hitch(this, function(results) {
				this._serverRole = results['server/role'];
				this._joined = results['joined'];
				this.standby(false);
			}), lang.hitch(this, function() {
				this.standby(false);
			}));

			// initial standby animation
			this.standby(true);
		},

		next: function(pageName) {
			var next = this.inherited(pageName);
			return this._initialDeferred.then(lang.hitch(this, function() {
				// block invalid server roles
				if (this._serverRole != 'domaincontroller_master' && this._serverRole != 'domaincontroller_slave' && this._serverRole != 'domaincontroller_backup') {
					dialog.alert(_('UCS@school can only be installed on the system roles DC master, DC backup, or DC slave.'));
					return 'setup';
				}

				// initial request
				return 'setup';

				// display the credentials page only on DC slave
				if (next === 'credentials' && this._serverRole != 'domaincontroller_slave') {
					next = 'samba';
				}

				return next;
			}));
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
