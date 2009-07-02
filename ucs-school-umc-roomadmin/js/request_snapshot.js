var umc = {};
umc.roomadmin = {};
umc.roomadmin.showSnapshot = function (node, sessionid, ipaddr) {
	var tmp_box = dojo.byId(ipaddr + '.screenshot');
	if (!tmp_box && node.parentNode) {
		var box = document.createElement('div');
		box.id                    = ipaddr + '.screenshot';
		box.style.marginLeft      = '2.2em';
		box.style.width           = '200px';
		box.style.height          = '150px';
		box.style.position        = 'absolute';
		box.style.border          = '2px outset black';
		box.style.backgroundColor = 'white';

		var img = new Image (200, 150);
		img.src = 'ajax.py?session_id='+sessionid+'&umcpcmd=roomadmin/italc/request/snapshot&ipaddr=' + ipaddr + '&date=' + new Date ().getTime ();
		box.appendChild (img);
		// this is an emulation for insertAfter
		node.parentNode.insertBefore (box, node.nextSibling);
	}
};

umc.roomadmin.updateSnapshot = function (sessionid, ipaddr) {
	var box = dojo.byId(ipaddr + '.screenshot');
	if (box && box.parentNode) {
		var img = box.firstChild;
		if (img) {
			img.src = 'ajax.py?session_id='+sessionid+'&umcpcmd=roomadmin/italc/request/snapshot&ipaddr=' + ipaddr + '&date=' + new Date ().getTime ();
		}
	}
};

umc.roomadmin.hideSnapshot = function (ipaddr) {
	var box = dojo.byId(ipaddr + '.screenshot');
	if (box && box.parentNode) {
		box.parentNode.removeChild (box);
	}
};

umc.roomadmin.store = null;
umc.roomadmin.updateData = function (sessionid, room) {
	var callback = function (item, request) {
		var username = dojo.byId (item.ipaddr + '.username');
		if (username) {
			if (!username.firstChild) {
				var txt = document.createTextNode ('');
				username.appendChild (txt);
			}
			if (username.firstChild.nodeValue != item.username) {
				dojo.fadeOut({node:username}).play ();
				username.firstChild.nodeValue = item.username;
				var a1 = dojo.fadeIn({node:username});
				var a2 = dojo.fadeOut({node:username});
				var a3 = dojo.fadeIn({node:username});
				var a4 = dojo.fadeOut({node:username});
				var a5 = dojo.fadeIn({node:username});
				var anim = dojo.fx.chain([a1, a2, a3, a4, a5]);
				anim.play();
			}
		}
		umc.roomadmin.updateSnapshot (sessionid, item.ipaddr);
		return false;
	};

	if (umc.roomadmin.store) {
		umc.roomadmin.store.close ()
	}
	umc.roomadmin.store = new dojo.data.ItemFileReadStore ({url:'ajax.py?session_id='+sessionid+'&umcpcmd=roomadmin/italc/request/data&room=' + room + '&date=' + new Date ().getTime ()});
	umc.roomadmin.store.fetch (
		{
			query: {ipaddr:'*'},
			onItem: callback
		}
	);
};

dojo.require ('dojo.data.ItemFileReadStore');
dojo.require ('dojo.fx');
