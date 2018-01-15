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
	"dojo/date/locale",
	"dojo/Deferred",
	"dijit/Dialog",
	"dojox/html/entities",
	"umc/dialog",
	"umc/tools",
	"umc/widgets/Module",
	"umc/widgets/Grid",
	"umc/widgets/Page",
	"umc/widgets/Form",
	"umc/widgets/SearchBox",
	"umc/widgets/TextBox",
	"umc/widgets/ComboBox",
	"umc/widgets/CheckBox",
	"umc/widgets/Text",
	"umc/widgets/ContainerWidget",
	"umc/widgets/ProgressInfo",
	"umc/widgets/SearchForm",
	"umc/i18n!umc/modules/schoolusers"
], function(declare, lang, array, locale, Deferred, Dialog, entities, dialog, tools, Module,
            Grid, Page, Form, SearchBox, TextBox, ComboBox, CheckBox, Text, ContainerWidget, ProgressInfo, SearchForm, _) {

	return declare("umc.modules.schoolusers", [ Module ], {
		idProperty: 'id',
		_grid: null,
		_searchPage: null,
		_progressInfo: null,

		uninitialize: function() {
			this.inherited(arguments);

			this._progressInfo.destroyRecursive();
		},

		buildRendering: function() {
			this.inherited(arguments);

			this.standbyOpacity = 1;
			this.standby(true);

			this._searchPage = new Page({
				fullWidth: true,
				headerText: this.description,
				helpText: ''
			});

			this.addChild(this._searchPage);

			var actions = [{
				name: 'reset',
				label: _('Reset password'),
				description: _('Resets password of user.'),
				isStandardAction: true,
				isMultiAction: true,
				callback: lang.hitch(this, '_resetPasswords')
			}];

			var columns = [{
				name: 'name',
				label: _('Name'),
				width: '60%'
			}, {
				name: 'passwordexpiry',
				label: _('Password expiration date'),
				width: '40%',
				'formatter': function(key) {
					if (key) {
						var date = locale.parse(key, { datePattern : 'yyyy-MM-dd', selector: 'date' });
						if (date) {
							return locale.format(date, { selector: 'date' });
						}
					}
					return '-';
				}
			}];

			this._grid = new Grid({
				actions: actions,
				columns: columns,
				moduleStore: this.moduleStore
			});

			this._searchPage.addChild(this._grid);

			var widgets = [{
				type: ComboBox,
				name: 'school',
				description: _('Select the school.'),
				label: _('School'),
				autoHide: true,
				size: 'TwoThirds',
				required: true,
				umcpCommand: lang.hitch(this, 'umcpCommand'),
				dynamicValues: 'schoolusers/schools'
			}, {
				type: ComboBox,
				name: 'class',
				description: _('Select a class or workgroup.'),
				label: _('Class or workgroup'),
				staticValues: [
					{ 'id' : 'None', 'label' : _('All classes and workgroups') }
				],
				dynamicValues: 'schoolusers/groups',
				umcpCommand: lang.hitch(this, 'umcpCommand'),
				depends: 'school'
			}, {
				type: SearchBox,
				name: 'pattern',
				size: 'TwoThirds',
				value: '',
				description: _('Specifies the substring pattern which is searched for in the first name, surname and username'),
				label: _('Name'),
				inlineLabel: _('Search...'),
				onSearch: lang.hitch(this, function() {
					this._searchForm.submit();
				})
			}];

			var layout = [
				[ 'school', 'class', 'pattern' ]
			];

			this._searchForm = new SearchForm({
				region: 'top',
				hideSubmitButton: true,
				widgets: widgets,
				layout: layout,
				onSearch: lang.hitch(this, function(values) {
					this._grid.filter(values);
				})
			});
			this.standbyDuring(this._searchForm.ready()).then(lang.hitch(this, function() {
				this.standbyOpacity = 0.75;
			}));

			this._searchPage.addChild(this._searchForm);

			this._progressInfo = new ProgressInfo({
				style: 'min-width: 400px'
			});

			this._searchPage.startup();

			tools.ucr(['ucsschool/passwordreset/autosearch', 'ucsschool/passwordreset/password-change-on-next-login', 'ucsschool/passwordreset/force-password-change-on-next-login']).then(lang.hitch(this, function(ucr) {
				this.changeOnNextLogin = tools.isTrue(ucr['ucsschool/passwordreset/password-change-on-next-login'] || true);
				this.changeOnNextLoginDisabled = tools.isTrue(ucr['ucsschool/passwordreset/force-password-change-on-next-login'] || false);
				if (tools.isTrue(ucr['ucsschool/passwordreset/autosearch'] || true)) {
					this._searchForm.ready().then(lang.hitch(this, function() {
						this._grid.filter(this._searchForm.get('value'));
					}));
				}
			}));
		},

		_resetPasswords: function( ids, items ) {
			var _dialog = null, form = null;

			var _cleanup = function() {
				_dialog.hide();
				_dialog.destroyRecursive();
				form.destroyRecursive();
			};

			var errors = [];
			var finished_func = lang.hitch( this, function() {
				this.moduleStore.onChange();
				this._progressInfo.update(ids.length, _('Finished'));
				this.standby(false);
				if (errors.length) {
					var message = _('Failed to reset the password for the following users:') + '<br><ul>';
					var _content = new ContainerWidget( {
						scrollable: true,
						style: 'max-height: 500px'
					});
					array.forEach(errors, function(item) {
						message += '<li>' + entities.encode(item.name) + '<br>' + entities.encode(item.message) + '</li>';
					});
					message += '</ul>';
					_content.addChild(new Text({ content: message }));
					dialog.alert(_content);
				}
			});

			var _set_passwords = lang.hitch(this, function(password, nextLogin) {
				var deferred = new Deferred();

				this._progressInfo.set('maximum', ids.length);
				this._progressInfo.updateTitle(_('Setting passwords'));
				deferred.resolve();
				this.standby(true, this._progressInfo);

				array.forEach(items, function(item, i) {
					deferred = deferred.then(lang.hitch(this, function() {
						this._progressInfo.update(i, _('User: ') + item.name);
						return this.umcpCommand('schoolusers/password/reset', {
							userDN: item.id,
							newPassword: password,
							nextLogin: nextLogin
						}, {
							display400: function(error) {
								errors.push({ name: item.name, message: error.message });
							}
						}).then(undefined, function(error) {
							return tools.parseError(error).status === 400;  // continue with the next user if an error occurred
						});
					}));
				}, this);

				// finish the progress bar and add error handler
				deferred = deferred.then(finished_func, finished_func);
			});

			var userType = (this.moduleFlavor === 'student' ?  _('students') : _('teachers'));
			form = new Form({
				style: 'max-width: 500px;',
				widgets: [{
					type: Text,
					name: 'info',
					// i18n: 0: number of selected users; 1 and 2: "students" / "teachers"
					content: '<p>' + lang.replace(_('Clicking the <i>Reset</i> button will set the password for all {0} selected {1} to the given password. For security reasons the {2} should be forced to change the password on the next login.'), [items.length, userType, userType]) + '</p>'
				},{
					type: CheckBox,
					name: 'changeOnNextLogin',
					value: this.changeOnNextLogin,
					disabled: this.changeOnNextLoginDisabled,
					label: _('User has to change password on next login')
				}, {
					name: 'newPassword',
					type: TextBox,
					required: true,
					label: _('New password')
				}],
				buttons: [{
					name: 'submit',
					label: _('Reset'),
					style: 'float: right;',
					callback: lang.hitch( this, function() {
						var nextLoginWidget = form.getWidget('changeOnNextLogin');
						var passwordWidget = form.getWidget('newPassword');

						if (!form.validate()) {
							passwordWidget.focus();
							return;
						}

						var password = passwordWidget.get('value');
						var nextLogin = nextLoginWidget.get('value');
						_cleanup();
						_set_passwords(password, nextLogin);
					} )
				}, {
					name: 'cancel',
					label: _('Cancel'),
					callback: _cleanup
				}],
				layout: ['info', 'changeOnNextLogin', 'newPassword']
			});

			_dialog = new Dialog( {
				title: _( 'Reset passwords' ),
				content: form,
				'class': 'umcPopup'
			} );
			_dialog.show();
		}
	});

});
