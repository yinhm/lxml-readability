// vim: set ts=8 sts=8 sw=8 noet:
/*
 * Copyright (c) 2006-2011 Echo <solutions@aboutecho.com>. All rights reserved.
 * You may copy and modify this script as long as the above copyright notice,
 * this condition and the following disclaimer is left intact.
 * This software is provided by the author "AS IS" and no warranties are
 * implied, including fitness for a particular purpose. In no event shall
 * the author be liable for any damages arising in any way out of the use
 * of this software, even if advised of the possibility of such damage.
 * $Id: reply.js 32046 2011-03-31 08:53:15Z jskit $
 */

(function($) {

var plugin = Echo.createPlugin({
	"name": "Reply",
	"applications": ["Stream"],
	"dependencies": [{
		"application": "Submit",
		"url": "//cdn.echoenabled.com/clientapps/v2.4.10/submit.js"
	}],
	"init": function(plugin, application) {
		plugin.vars = plugin.vars || {};
		plugin.extendRenderer("Item", "children", plugin.renderers.Item.children);
		plugin.extendRenderer("Item", "replyForm", plugin.renderers.Item.replyForm);
		plugin.extendRenderer("Item", "container", plugin.renderers.Item.container);
		plugin.extendTemplate("Item", plugin.template, "insertAfter", "echo-item-children");
		plugin.listenEvents(application);
		plugin.addItemControl(application, plugin.assembleControl("Reply", application));
	}
});

plugin.template = '<div class="echo-item-replyForm"></div>';

plugin.addLabels({
	"replyControl": "Reply"
});

plugin.assembleControl = function(name, application) {
	var callback = function() {
		var item = this;
		var target = item.dom.get("replyForm");
		if (!plugin.get(item, "form")) {
			plugin.createForm(item, target);
		}
		if (plugin.get(item, "form.initialized")) {
			if (!item.children.length) {
				plugin.view(item, "toggle");
				item.rerender("container");
			}
		} else {
			item.rerender("replyForm");
		}
		var form = plugin.get(item, "form");
		form.instance.switchMode();
		if (form.visible) {
			if (form.instance.dom) {
				text = form.instance.dom.get("text");
				if (text && text.is(":visible")) {
					text.focus();
					return;
				}
			}
			target.get(0).scrollIntoView(false);
		}
	};
	return function() {
		var item = this;
		return {
			"name": "Reply",
			"label": plugin.label("replyControl"),
			"visible": !item.depth,
			"callback": callback
		};
	};
};

plugin.renderers = {"Item": {}};

plugin.renderers.Item.children = function(element, dom) {
	var item = this;
	item.rerender("replyForm");
	item.parentRenderer("children", arguments);
};

plugin.renderers.Item.replyForm = function(element, dom) {
	var item = this;
	if (item.depth) return;
	if ((!item.depth && item.children.length && !plugin.get(item, "form")) ||
		plugin.get(plugin, plugin.getFormKey(item))) {
			plugin.createForm(item, element);
	} else if (!plugin.get(item, "form")) return;
	var hasChildren = !!item.children.length;
	if (!plugin.get(item, "form.initialized")) {
		plugin.set(item, "form.initialized", true);
		element.addClass("echo-item-container echo-item-container-child " +
			"echo-trinaryBackgroundColor echo-item-depth-" + (item.depth + 1));
		if (!hasChildren) {
			item.rerender("container");
		} else if (plugin.get(item, "form.visible")) {
			plugin.view(item, "show");
		}
	} else {
		if (plugin.get(item, "form.visible") &&
			(!hasChildren || item.children.length == 1 && item.children[0].deleted)) {
				plugin.view(item, "hide");
		} else if (hasChildren) {
			plugin.view(item, "show");
		}
	}
};

plugin.renderers.Item.container = function(element, dom) {
	var item = this;
	var threading = item.threading;
	if (plugin.get(item, "form.visible")) {
		item.threading = true;
	}
	item.parentRenderer("container", arguments);
	item.threading = threading;
};

plugin.prepareParams = function(application, item) {
	return application.prepareBroadcastParams({
		"plugin": plugin.name,
		"form": plugin.get(item, "form"),
		"item": {
			"data": item.data,
			"target": item.dom.content
		}
	});
};

plugin.listenEvents = function(application) {
	$.map(["Expand", "Collapse"], function(action) {
		plugin.subscribe(application, "Submit.on" + action, function(event, args) {
			var item = application.items[args.data.unique];
			if (!item || !plugin.get(item, "form")) return;
			if (action == "Collapse" && !item.children.length) {
				plugin.view(item, "hide");
				item.rerender("container");
			}
			var topic = plugin.topic(application, "onForm" + action);
			plugin.publish(application, topic, plugin.prepareParams(application, item));
		});
	});
	plugin.subscribe(application, "Submit.onPostComplete", function(topic, args) {
		var item = application.items[args.data.unique];
		if (!item) return;
		plugin.get(item, "form.instance").switchMode("compact");
	});
};

plugin.createForm = function(item, target) {
	var config = plugin.assembleConfig(item, {
		"target": target.get(0),
		"data":  {"unique": item.data.unique},
		"mode": "compact",
		"targetURL": item.id
	});
	var key = plugin.getFormKey(item);
	var form = (plugin.get(plugin, key) || {}).instance;
	if (form) {
		var text = form.dom.get("text").val();
		form.config.set("target", target);
		target.empty().append(form.render());
		if (text) {
			form.dom.get("text").val(text);
		}
	} else {
		form = new Echo.Submit(config);
	}
	var data = {
		"instance": form,
		"initialized": false,
		"visible": true
	};
	plugin.set(plugin, key, data);
	plugin.set(item, "form", data);
};

plugin.view = function(item, action) {
	var visibility = action == "toggle"
		? !plugin.get(item, "form.visible")
		: action == "show";
	plugin.set(item, "form.visible", visibility);
	plugin.get(item, "form.instance").config.get("target")[action]();
};

plugin.getFormKey = function(item) {
	return "forms." + item.data.unique + "-" + item.getContextId();
};

})(jQuery);


