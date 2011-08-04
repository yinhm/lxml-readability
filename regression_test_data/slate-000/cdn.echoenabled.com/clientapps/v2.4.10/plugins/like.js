// vim: set ts=8 sts=8 sw=8 noet:
/*
 * Copyright (c) 2006-2011 Echo <solutions@aboutecho.com>. All rights reserved.
 * You may copy and modify this script as long as the above copyright notice,
 * this condition and the following disclaimer is left intact.
 * This software is provided by the author "AS IS" and no warranties are
 * implied, including fitness for a particular purpose. In no event shall
 * the author be liable for any damages arising in any way out of the use
 * of this software, even if advised of the possibility of such damage.
 * $Id: like.js 32046 2011-03-31 08:53:15Z jskit $
 */

(function($) {

var plugin = Echo.createPlugin({
	"name": "Like",
	"applications": ["Stream"],
	"dependencies": [{
		"application": "UserList",
		"url": "//cdn.echoenabled.com/clientapps/v2.4.10/user-list.js"
	}],
	"init": function(plugin, application) {
		plugin.extendRenderer("Item", "likes", plugin.renderers.Item.users);
		plugin.extendTemplate("Item", plugin.template,
			"insertAsLastChild", "echo-item-data");
		plugin.addItemControl(application, plugin.assembleControl("Like", application));
		plugin.addItemControl(application, plugin.assembleControl("Unlike", application));
		plugin.addCss(plugin.css);
	}
});

plugin.template = '<div class="echo-item-likes"></div>';

plugin.addLabels({
	"likeThis": " like this.",
	"likesThis": " likes this.",
	"likeControl": "Like",
	"unlikeControl": "Unlike",
	"likeProcessing": "Liking...",
	"unlikeProcessing": "Unliking..."
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
		var action =
			($.map(item.data.object.likes, function(entry) {
				if (item.user.hasIdentity(entry.actor.id)) return entry;
			})).length > 0 ? "Unlike" : "Like";
		return {
			"name": name,
			"label": plugin.label(name.toLowerCase() + "Control"),
			"visible": item.user.logged() && action == name,
			"onetime": true,
			"callback": callback
		};
	};
};

plugin.renderers = {"Item": {}};

plugin.renderers.Item.users = function(element, dom) {
	var item = this;
	if (!item.data.object.likes.length) {
		element.hide();
		return;
	}
	var likesPerPage = 5;
	var visibleUsersCount = plugin.get(item, "userList")
		? plugin.get(item, "userList").getVisibleUsersCount()
		: likesPerPage;
	var youLike = false;
	var users = $.map(item.data.object.likes, function(like) {
		if (like.actor.id == item.user.get("id")) {
			youLike = true;
		}
		return like.actor;
	});
	var config = plugin.assembleConfig(item, {
		"target": element.get(0),
		"data": users,
		"itemsPerPage": likesPerPage,
		"suffixText": plugin.label(users.length > 1 || youLike ? "likeThis" : "likesThis"),
		"totalUsersCount": item.data.object.accumulators.likesCount,
		"visibleUsersCount": visibleUsersCount
	});
	plugin.set(item, "userList", new Echo.UserList(config));
	element.show();
};

plugin.css = '.echo-item-likes { line-height: 16px; background: url(//c0.echoenabled.com/images/likes.png) no-repeat 0px 4px; padding: 0px 0px 4px 21px; }';

})(jQuery);


