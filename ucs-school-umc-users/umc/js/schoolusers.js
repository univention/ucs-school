/*
 * Copyright 2012-2024 Univention GmbH
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
	"dojo/on",
	"dojo/Deferred",
	"dojox/html/entities",
	"umc/dialog",
	"umc/tools",
	"umc/widgets/Dialog",
	"umc/widgets/Module",
	"umc/widgets/Grid",
	"umc/widgets/Page",
	"umc/widgets/Form",
	"umc/widgets/SearchBox",
	"umc/widgets/PasswordBox",
	"umc/widgets/ComboBox",
	"umc/widgets/CheckBox",
	"umc/widgets/Text",
	"umc/widgets/ContainerWidget",
	"umc/widgets/ProgressBar",
	"umc/widgets/SearchForm",
	"umc/i18n!umc/modules/schoolusers"
], function(declare, lang, array, on, Deferred, entities, dialog, tools, Dialog, Module, Grid, Page, Form, SearchBox,
		PasswordBox, ComboBox, CheckBox, Text, ContainerWidget, ProgressBar, SearchForm, _) {

	return declare("umc.modules.schoolusers", [ Module ], {
		idProperty: 'id',
		_grid: null,
		_searchPage: null,
		_progressBar: null,
		_initialChangeDone: false,

		selectablePagesToLayoutMapping: {
			_searchPage: 'searchpage-grid'
		},

		buildRendering: function() {
			this.inherited(arguments);

			this._searchPage = new Page({
				fullWidth: true
			});

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
				label: _('Password change required'),
				width: '40%',
				formatter: function(key) {
					var days = Number(key);
					if (days == -1) {
						return _('never');
					} else if (days == 0) {
						return _('now');
					} else if (isNaN(days)) { // This should never happen!
						return "NaN";
					} else if (days == 1) {
						return _('in %s day', days);
					} else {
						return _('in %s days', days);
					}
				}
			}];

			this._grid = new Grid({
				actions: actions,
				hideContextActionsWhenNoSelection: false,
				columns: columns,
				moduleStore: this.moduleStore,
				defaultAction: 'reset'
			});

			var widgets = [{
				type: ComboBox,
				'class': 'umcTextBoxOnBody',
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
				'class': 'umcTextBoxOnBody',
				name: 'class',
				size: 'TwoThirds',
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
				'class': 'umcTextBoxOnBody',
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

			tools.ucr(['ucsschool/passwordreset/autosearch', 'ucsschool/passwordreset/autosearch_on_change']).then(lang.hitch(this, function(ucr) {
				this._searchForm.ready().then(lang.hitch(this, function() {
					var _school = this._searchForm.getWidget('school');
					var _class = this._searchForm.getWidget('class');

					on(_school, 'change', lang.hitch(this, function() {
						var classBeforeChange = _class.get('value');
						on.once(_class, 'valuesLoaded', lang.hitch(this, function() {
							_class.set('value', 'None');
							_class._saveInitialValue();
							if (classBeforeChange === 'None' && tools.isTrue(ucr['ucsschool/passwordreset/autosearch_on_change'] || true)) {
								this._searchForm.submit();
							}
						}));
					}));

					on(_class, 'change', lang.hitch(this, function() {
						if (!this._initialChangeDone) {
							if (tools.isTrue(ucr['ucsschool/passwordreset/autosearch'] || true)) {
								this._searchForm.submit();
							}
							this._initialChangeDone = true;
							return;
						}

						if (tools.isTrue(ucr['ucsschool/passwordreset/autosearch_on_change'] || true)) {
							this._searchForm.submit();
						}
					}));
				}));
			}));

			this._progressBar = new ProgressBar({
				style: 'min-width: 400px'
			});
			this.own(this._progressBar);

			this.standbyDuring(this._searchForm.ready());
			this._searchPage.addChild(this._searchForm);
			this._searchPage.addChild(this._grid);
			this.addChild(this._searchPage);

			tools.ucr(['ucsschool/passwordreset/password-change-on-next-login', 'ucsschool/passwordreset/force-password-change-on-next-login']).then(lang.hitch(this, function(ucr) {
				this.changeOnNextLogin = tools.isTrue(ucr['ucsschool/passwordreset/password-change-on-next-login'] || true);
				this.changeOnNextLoginDisabled = tools.isTrue(ucr['ucsschool/passwordreset/force-password-change-on-next-login'] || false);
			}));
		},

		_resetPasswords: function( ids, items ) {
			var _dialog = null, form = null;

			var _cleanup = function() {
				_dialog.close();
			};

			var errors = [];
			var finished_func = lang.hitch( this, function() {
				this.moduleStore.onChange();
				this._progressBar.setInfo(null, _('Finished'), 100);
				this.standby(false);
				if (errors.length) {
					var message = _('Failed to reset the password for the following users:') + '<br><ul>';
					var _content = new ContainerWidget( {
						style: 'max-height: 500px;'
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

				this._progressBar.setInfo(_('Setting passwords'));
				deferred.resolve();
				this.standby(true, this._progressBar);

				array.forEach(items, function(item, i) {
					deferred = deferred.then(lang.hitch(this, function() {
						this._progressBar.setInfo(null, _('User: ') + item.name, (i / ids.length) * 100);
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

			if (this.moduleFlavor === 'student') {
			   var userType = _('students');
			} else if (this.moduleFlavor === 'teacher') {
			   var userType = _('teachers');
			} else {
			   var userType = _('staff');
			}
			form = new Form({
				style: 'max-width: 500px;',
				widgets: [{
					type: Text,
					name: 'info',
					// i18n: 0: number of selected users; 1 and 2: "students" / "teachers"
					content: '<p>' + lang.replace(_('Clicking the <i>Reset</i> button will set the password for all selected {1} to the given password. For security reasons the {2} will be forced to change the password on the next login.'), [items.length, userType, userType]) + '</p>'
				},{
					type: CheckBox,
					name: 'changeOnNextLogin',
					value: this.changeOnNextLogin,
					disabled: this.changeOnNextLoginDisabled,
					label: _('User has to change password on next login')
				}, {
					name: 'newPassword',
					type: PasswordBox,
					showRevealToggle: true,
					required: true,
					label: _('New password')
				}],
				buttons: [{
					name: 'cancel',
					label: _('Cancel'),
					callback: _cleanup,
					align: 'left'
				}, {
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
				}],
				layout: ['info', 'changeOnNextLogin', 'newPassword']
			});

			_dialog = new Dialog( {
				title: _( 'Reset passwords'),
				content: form,
				destroyOnCancel: true
			} );
			_dialog.show();
		}
	});

});
