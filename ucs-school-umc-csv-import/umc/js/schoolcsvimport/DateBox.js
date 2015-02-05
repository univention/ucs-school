/*
 * Copyright 2014-2015 Univention GmbH
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
	"dojo/date/locale",
	"umc/widgets/DateBox"
], function(declare, dateLocale, DateBox) {
	return declare('umc.modules.schoolcsvimport.DateBox', [ DateBox ], {
		datePattern: 'yyyy-MM-dd',

		buildRendering: function() {
			this.inherited(arguments);
			this._dateBox.set('constraints', this._getConstraints());
			//this._dateBox.constraints.fullYear = false; // hard coded!
		},

		_getConstraints: function() {
			return {datePattern: this.datePattern, selector: 'date'};
		},

		"parse": function(val) {
			return this._dateBox.parse(val, this._getConstraints());
		},

		_setValueAttr: function(/*String|Date*/ newVal) {
			newVal = this.parse(newVal);
			this._dateBox.set('value', newVal);
		},

		_dateToString: function(dateObj) {
			if (dateObj && dateObj instanceof Date) {
				return dateLocale.format(dateObj, this._getConstraints());
			}
			return dateObj;
		}
	});
});

