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
	"dojo/_base/array",
	"dojo/dom-class",
	"dojo/dom-style",
	"dojo/on",
	"dojo/topic",
	"umc/dialog",
	"umc/tools",
	"umc/widgets/Wizard",
	"umc/widgets/Module",
	"umc/widgets/TextBox",
	"umc/widgets/TextArea",
	"umc/widgets/ComboBox",
	"umc/widgets/MultiObjectSelect",
	"umc/widgets/MultiUploader",
	"umc/i18n!umc/modules/schoolexam"
], function(declare, lang, array, domClass, domStyle, on, topic, dialog, tools, Wizard, Module, TextBox, TextArea, ComboBox, MultiObjectSelect, MultiUploader, _) {
	return declare("umc.modules.schoolexam", [ Module, Wizard ], {
		// summary:
		//		Template module to ease the UMC module development.
		// description:
		//		This module is a template module in order to aid the development of
		//		new modules for Univention Management Console.

		postMixInProperties: function() {
			this.inherited(arguments);

			var myRules = _( 'Personal internet rules' );

			this.pages = [{
				name: 'general',
				headerText: _('Start a new exam'),
				helpText: _('<p>The UCS@school exam mode allows one to perform an exam in a computer room. During the exam, access to internet as well as to shares can be restricted, the student home directories are not accessible, either.</p><p>Please enter a name for the new exam and select the classes or workgroups that participate in the exam. A directory name is proposed automatically and can be adjusted if wanted.</p>'),
				widgets: [{
					type: ComboBox,
					name: 'school',
					description: _('Choose the school'),
					label: _('School'),
					dynamicValues: 'schoolexam/schools',
					autoHide: true
				}, {
					type: ComboBox,
					name: 'room',
					label: _('Computer room'),
					description: _('Choose the computer room in which the exam will take place'),
					depends: 'school',
					dynamicValues: 'schoolexam/rooms'
				}, {
					name: 'name',
					type: TextBox,
					label: _('Exam name'),
					description: _('The name of the exam, e.g., "Math exam algrebra 02/2013".')
				}, {
					name: 'directory',
					type: TextBox,
					label: _('Directory name'),
					description: _('The name of the project directory as it will be displayed in the file system.'),
					depends: ['name'],
					dynamicValue: lang.hitch(this, function(values) {
						// avoid certain characters for the directory name
						var name = values.name;
						array.forEach([/\//g, /\\/g, /\?/g, /%/g, /\*/g, /:/g, /\|/g, /"/g, /</g, />/g, /\$/g, /'/g], function(ichar) {
							name = name.replace(ichar, '_');
						});

						// limit the filename length
						return name.slice(0, 255);
					})
				}, {
					type: MultiObjectSelect,
					name: 'recipients',
					dialogTitle: _('Assign classes/workgroups'),
					label: _('Assigned classes/workgroups'),
					description: _('List of groups that are marked to receive the teaching materials'),
					queryWidgets: [{
						type: ComboBox,
						name: 'school',
						label: _('School'),
						dynamicValues: 'schoolexam/schools',
						umcpCommand: this.umcpCommand,
						autoHide: true
					}, {
						type: TextBox,
						name: 'pattern',
						label: _('Search name')
					}],
					queryCommand: lang.hitch(this, function(options) {
						return this.umcpCommand('schoolexam/groups', options).then(function(data) {
							return data.result;
						});
					}),
					autoSearch: true
				}]
			}, {
				name: 'files',
				headerText: _('Upload of exam files'),
				helpText: _('Please select all necessary files for the exam and upload them one by one. These files will be distributed to all participating students. A copy of the original files will be stored in your home directory, as well. During the exam or at the end of it, the corresponding files can be collected from the students. The collected files will be stored in your home directory, as well.'),
				widgets: [{
					type: MultiUploader,
					name: 'files',
					// TODO: correct UMCP command name
					command: 'schoolexam/upload',
					label: _('Files'),
					description: _('Files that are distributed along with this exam')
					//canUpload: lang.hitch(this, '_checkFilenameUpload'),
					//canRemove: lang.hitch(this, '_checkFilenamesRemove')
				}]
			}, {
				name: 'roomSettings',
				headerText: _('Computer room settings'),
				helpText: _('Please select the access restrictions to internet as well as to shares. These settings can also be adjusted during the exam via the room settings in the module <i>Computer room</i>. Note that the student home directories are not accessible during the exam mode.'),
				widgets: [{
					type: ComboBox,
					name: 'shareMode',
					sizeClass: 'One',
					label: _('Share access'),
					description: _( 'Defines restriction for the share access' ),
					staticValues: [
						{ id: 'home', label : _('Home directory only') },
						{ id: 'all', label : _('No restrictions' ) }
					]
				}, {
					type: ComboBox,
					name: 'internetRule',
					label: _('Web access profile'),
					dynamicValues: 'schoolexam/internetrules',
					staticValues: [
						{ id: 'none', label: _( 'Default (global settings)' ) },
						{ id: 'custom', label: myRules }
					],
					onChange: lang.hitch(this, function(value) {
						this.getWidget('roomSettings', 'customRule').set( 'disabled', value != 'custom');
					})
				}, {
					type: TextArea,
					name: 'customRule',
					label: lang.replace( _( 'List of allowed web sites for "{myRules}"' ), {
						myRules: myRules
					} ),
					sizeClass: 'One',
					description: _( '<p>In this text box you can list web sites that are allowed to be used by the students. Each line should contain one web site. Example: </p><p style="font-family: monospace">univention.com<br/>wikipedia.org<br/></p>' ),
					validate: lang.hitch( this, function() {
						return !( this._form.getWidget( 'internetRule' ).get( 'value' ) == 'custom' && ! this._form.getWidget( 'customRule' ).get( 'value' ) );
					} ),
					onFocus: lang.hitch( this, function() {
						//dijit.hideTooltip( this._form.getWidget( 'customRule' ).domNode ); // FIXME
					} ),
					disabled: true
				}]
			}];
		},

		buildRendering: function() {
			this.inherited(arguments);


			// TODO set maxsize
			//maxSize: maxUploadSize * 1024, // conversion from kbyte to byte
		},

		_updateButtons: function(pageName) {
			this.inherited(arguments);

			// the wizard can always be finished
			var buttons = this._pages[pageName]._footerButtons;
			domClass.toggle(buttons.finish.domNode, 'dijitHidden', false);
			if (this.hasNext(pageName)) {
				// make sure that ther is a little space between the two buttons 'next' and 'finish'
				domStyle.set(buttons.finish.domNode, { marginLeft: '5px' });
			}
		}
	});
});
