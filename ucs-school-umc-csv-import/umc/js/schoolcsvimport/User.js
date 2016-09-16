/*
 * Copyright 2014-2016 Univention GmbH
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
	"dojo/_base/kernel",
	"dojo/_base/lang",
	"dojo/_base/array",
	"dojo/query",
	"dojo/dom-style",
	"umc/tools",
	"umc/widgets/Tooltip",
	"umc/i18n!umc/modules/schoolcsvimport"
], function(kernel, lang, array, query, style, tools, Tooltip, _) {
	var User = function(values) {
		this._initialValues = lang.clone(values);
		this.setValues(values);
	};

	kernel.extend(User, {
		restore: function() {
			this.setValues(this._initialValues);
		},

		toObject: function() {
			var obj = {};
			tools.forIn(this._initialValues, lang.hitch(this, function(k) {
				if (k in this) {
					obj[k] = this[k];
					if (k == 'school_classes' && typeof this[k] != 'object') {
						obj[k] = {}
						obj[k][this.school] = this[k] ? this[k].split(',') : [];
					}
				}
			}));
			return obj;
		},

		setValues: function(values) {
			tools.forIn(values, lang.hitch(this, function(k, v) {
				if (k == 'school_classes' && typeof v == 'object') {
					var val = [];
					tools.forIn(v, function(school, classes) {
						array.forEach(classes, function(school_class) {
							val.push(school_class);
						});
					});
					v = val.join(',');
				}
				this[k] = v;
			}));
		},

		resetError: function() {
			this.errors = {};
			this.warnings = {};
			this.errorState = ['all-good'];
			if (this.action == 'ignore') {
				return;
			}
			tools.forIn(this._initialValues.errors, lang.hitch(this, function(field, notes) {
				array.forEach(notes, lang.hitch(this, function(note) {
					this.setError(field, note);
				}));
			}));
			tools.forIn(this._initialValues.warnings, lang.hitch(this, function(field, notes) {
				array.forEach(notes, lang.hitch(this, function(note) {
					this.setWarning(field, note);
				}));
			}));
		},

		setWarning: function(field, note) {
			var warnings = this.warnings[field];
			if (!warnings) {
				warnings = this.warnings[field] = [];
			}
			warnings.push(note);
			this.errorState = 'not-all-good';
		},

		setError: function(field, note) {
			var errors = this.errors[field];
			if (!errors) {
				errors = this.errors[field] = [];
			}
			errors.push(note);
			this.errorState = 'not-all-good';
		},

		styleError: function(grid, row) {
			var hasIssues = false;
			tools.forIn(this.warnings, function(field) {
				hasIssues = true;
				row.customStyles += 'background-color: #FFFFE0;'; // lightyellow
				var cellIndex;
				array.forEach(grid.get('structure'), function(struct, i) {
					if (struct.field == field) {
						cellIndex = i + 1;
					}
				});
				var cellNode = query('.dojoxGridCell[idx$=' + cellIndex +']', row.node)[0];
				if (cellNode) {
					style.set(cellNode, {
						backgroundColor: '#FFFF00' // yellow
					});
				}
			});
			tools.forIn(this.errors, function(field) {
				hasIssues = true;
				row.customStyles += 'background-color: #F08080;'; // lightcoral
				var cellIndex;
				array.forEach(grid.get('structure'), function(struct, i) {
					if (struct.field == field) {
						cellIndex = i + 1;
					}
				});
				var cellNode = query('.dojoxGridCell[idx$=' + cellIndex +']', row.node)[0];
				if (cellNode) {
					style.set(cellNode, {
						backgroundColor: '#FF0000', // red
						color: '#FFFFFF' // white, because of contrast
					});
				}
			});
			if (hasIssues) {
				var completeErrorMessage = _('The following issues arose while checking this row:');
				completeErrorMessage += '<ul style="margin-left: -2em;">';
				array.forEach(grid.get('structure'), lang.hitch(this, function(struct) {
					var field = struct.field;
					var label = grid.getCellByField(field).name;
					var issues = lang.clone(this.errors[field] || []);
					issues = issues.concat(this.warnings[field] || []);
					if (issues.length) {
						completeErrorMessage += '<li>' + label + '<ul style="margin-left: -2em;">';
						array.forEach(issues, function(issue) {
							completeErrorMessage += '<li>' + issue + '</li>';
						});
						completeErrorMessage += '</ul></li>';
					}
				}));
				completeErrorMessage += '</ul>';
				var tooltip = new Tooltip({
					label: completeErrorMessage,
					connectId: [row.node]
				});
				grid.own(tooltip);
			}
		}
	});

	return User;
});

