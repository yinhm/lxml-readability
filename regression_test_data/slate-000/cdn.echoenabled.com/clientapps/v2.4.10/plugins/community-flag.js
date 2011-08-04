// vim: set ts=8 sts=8 sw=8 noet:
/*
 * Copyright (c) 2006-2011 Echo <solutions@aboutecho.com>. All rights reserved.
 * You may copy and modify this script as long as the above copyright notice,
 * this condition and the following disclaimer is left intact.
 * This software is provided by the author "AS IS" and no warranties are
 * implied, including fitness for a particular purpose. In no event shall
 * the author be liable for any damages arising in any way out of the use
 * of this software, even if advised of the possibility of such damage.
 * $Id: community-flag.js 32046 2011-03-31 08:53:15Z jskit $
 */

(function($) {

var plugin = Echo.createPlugin({
	"name": "CommunityFlag",
	"applications": ["Stream"],
	"init": function(plugin, application) {
		plugin.addItemControl(application, plugin.assembleControl("Flag", application));
		plugin.addItemControl(application, plugin.assembleControl("Unflag", application));
	}
});

plugin.addLabels({
	"flagControl": "Flag",
	"unflagControl": "Unflag",
	"flagProcessing": "Flagging...",
	"unflagProcessing": "Unflagging..."
});

plugin.assembleControl = function(name, application) {
	var callback = function() {
		var item = this;
		item.controls[plugin.name + "." + name].element
			.empty()
			.append(plugin.label(name.toLowerCase() + "Processing"));
		$.get(plugin.config.get(application, "submissionProxyURL", "", true), {
			"appkey": application.config.get("appkey"),
			"content": $.object2JSON({
				"verb": name.toLowerCase(),
				"target": item.id
			}),
			"sessionID": item.user.get("sessionID", "")
		}, function() {
			var topic = plugin.topic(application, "on" + name + "Complete");
			plugin.publish(application, topic, application.prepareBroadcastParams({
				"item": {
					"data": item.data,
					"target": item.dom.content
				}
			}));
			application.startLiveUpdates(true);
		}, "jsonp");
	};
	return function() {
		var item = this;
		var count = item.data.object.flags.length;
		var action =
			($.map(item.data.object.flags, function(entry) {
				if (item.user.hasIdentity(entry.actor.id)) return entry;
			})).length > 0 ? "Unflag" : "Flag";
		return {
			"name": name,
			"label": '<span class="echo-clickable">' + plugin.label(name.toLowerCase() + "Control") + '</span>' +
				(item.user.isAdmin() && count ? " (" + count + ")" : ""),
			"visible": item.user.logged() && action == name,
			"onetime": true,
			"callback": callback
		};
	};
};

})(jQuery);


