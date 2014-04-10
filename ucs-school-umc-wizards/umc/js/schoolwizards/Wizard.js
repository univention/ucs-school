/*
 * Copyright 2012-2014 Univention GmbH
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
	"umc/dialog",
	"umc/tools",
	"umc/widgets/Wizard",
	"umc/i18n!umc/modules/schoolwizards"
], function(declare, lang, dialog, tools, Wizard, _) {

	return declare("umc.modules.schoolwizards.Wizard", [Wizard], {

		umcpCommand: null,
		description: null,
		store: null,

		editMode: null,  // flag for edit mode
		$dn$: null,  // the object we edit
		school: null,  // the school of that object

		loadingDeferred: null,

		startup: function() {
			this.inherited(arguments);
			if (this.editMode) {
				this.loadingDeferred = this.standbyDuring(this.loadValues());
			}
		},

		loadValues: function() {
			var load = this.store.get({
				$dn$: this.$dn$
			});
			load.then(lang.hitch(this, function(result) {
				tools.forIn(result, lang.hitch(this, function(key, value) {
					var widget = this.getWidget(key);
					if (widget) {
						widget.set('value', value);
					}
				}));
			}));
			return load;
		},

		hasNext: function() {
			return true;
		},

		next: function(/*String*/ currentPage) {
			var nextPage = this.inherited(arguments);
			this.updateWidgets(currentPage);
			if (this._getPageIndex(currentPage) === (this.pages.length - 1 )) {
				if (this._validateForm()) {
					if (this.editMode) {
						return this.finishEditMode(currentPage);
					} else {
						return this.finishAddMode(currentPage);
					}
				} else {
					return currentPage;
				}
			}
			return nextPage;
		},

		finishAddMode: function(currentPage) {
			return this._createObject().then(lang.hitch(this, function(result) {
				if (result) {
					this.addNote();
					this.restart();
					this.focusFirstWidget(currentPage);
				}
				return currentPage;
			}));
		},

		finishEditMode: function(currentPage) {
			var values = this.getValues();
			return this.standbyDuring(this.store.put(values)).then(lang.hitch(this, function(response) {
				this.onFinished();  // close this wizard
				return currentPage;
			}));
		},

		_validateForm: function() {
			var form = this.selectedChildWidget.get('_form');
			if (!form.validate()) {
				var widgets = form.getInvalidWidgets();
				form.getWidget(widgets[0]).focus();
				return false;
			}
			return true;
		},

		_createObject: function() {
			var values = this.getValues();
			return this.standbyDuring(this.store.add(values)).then(lang.hitch(this, function(response) {
				if (response.result) {
					dialog.alert(response.result.message);
					return false;
				}
				return true;
			}), lang.hitch(this, function(result) { return false; }));
		},

		restart: function() {
		},

		updateWidgets: function(/*String*/ currentPage) {
		},

		focusFirstWidget: function(pageName) {
			// Determine the name of the first widget
			var layout = this.getPage(pageName)._form.get('layout');
			while (layout instanceof Array) {
				layout = layout[0];
			}
			this.getWidget(pageName, layout).focus();
		}
	});
});
