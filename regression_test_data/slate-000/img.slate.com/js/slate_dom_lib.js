// Cross-browser methods for DOM functions
var SlateDom = {};
// ELEMENT FUNCTIONS
SlateDom.getTarget = function(evt)//event
{
	var tar;
	if(!evt) var e = window.event;
	if(evt.target) tar = evt.target;
	else if(evt.srcElement) tar = evt.srcElement;
	if (tar.nodeType==3) tar = tar.parentNode;//for Safari bug
	
	return tar;
}

SlateDom.newElement = function(tagName,contents,id,className)
{
	var elm = document.createElement(tagName);
	if (id)	elm.id = id;
	if (className)	elm.className = className;
	if (contents) elm.innerHTML = contents;
	return elm;
}

SlateDom.addListener = function(obj,type,handler) //object,string,function 
{	
	if(typeof document.addEventListener != "undefined")
	{
		if(type.indexOf("on") == 0)
		{
			type = type.substr(2);
		}
		obj.addEventListener(type,handler,true);
	}
	else if(document.attachEvent != "undefined")
	{
		if(type.indexOf("on") != 0)
		{
			type = "on" + type;
		}
		obj.attachEvent(type,handler)
	}
	else
	{
		throw("[SLATE DOM ERROR] can't add listener");
	}
}

SlateDom.dropListener = function(obj,type,handler) //object,string,function 
{	
	if(typeof document.removeEventListener != "undefined")
	{
		if(type.indexOf("on") == 0)
		{
			type = type.substr(2);
		}
		obj.removeEventListener(type,handler,true);
	}
	else if(document.detachEvent != "undefined")
	{
		if(type.indexOf("on") != 0)
		{
			type = "on" + type;
		}
		obj.detachEvent(type,handler)
	}
	else
	{
		throw("[SLATE DOM ERROR] can't drop listener");
	}
}

SlateDom.dispatchEvent = function(obj,type)
{
	var evt;
	
	if(typeof document.dispatchEvent != "undefined")
	{
		if(type.indexOf("on") == 0)
		{
			type = type.substr(2);
		}
		evt = document.createEvent("MouseEvents");
		evt.initMouseEvent(type, true, true, window, 0, 0, 0, 0, 0, false, false, false, false, 0, null);
		obj.dispatchEvent(evt);
	}
	else if(document.fireEvent != "undefined")
	{
		if(type.indexOf("on") != 0)
		{
			type = "on" + type;
		}
		obj.fireEvent(type);
	}
	else
	{
		throw("[SLATE DOM ERROR] can't dispatch event");
	}
}

SlateDom.getCurrentStyle = function(elm,prop)
{
	var style;
	if(window.getComputedStyle)
	{
		style = window.getComputedStyle(elm,null).getPropertyValue(prop);
	}
	else if(elm.currentStyle)
	{
		style = elm.currentStyle[prop];	
	}
	return style;
}

SlateDom.getElementsByClassName = function(nodeList, className)//nodeList, string
{
	var nodes, qname, cnames, matches;
	
	nodes = nodeList;
	qname = className;
	matches = [];	
	
	for(var i=0; i<nodes.length; i++)
	{
		cnames = nodes[i].className.split(" ");
		
		for(var j=0; j<cnames.length; j++)
		{
			if(cnames[j]==qname)
			{
				matches.push(nodes[i]);
			}
		}
	}
	return matches;
}

SlateDom.hideElement = function(elm)//element
{
	elm.style.display = "none";
}

//FORM FUNCTIONS
SlateDom.newInputElement = function(type,name,value)
{
	var input;
	input = document.createElement("input");
	input.setAttribute("type",type);
	input.setAttribute("name",name);
	input.setAttribute("value",value);

	return input;
}
//INTERACTIVITY AND ANIMATION
SlateDom.setAsButton = function(elm,bool)
{
	if(bool)
	{
		elm.style.cursor="pointer";
	}
	else
	{
		elm.style.cursor="default";	
	}
}
SlateDom.tweenProperty = function(id,p,um,st,end,dur,cb)
{
	var elmId = id;//string or object. id of the element to tween, or the element itself
	var unitOfMeasure = um;//string.
	var prop = p;//string. css property to tween, must be a propert with a numeric value
	var startVal = st;//integer
	var endVal = end;//integer
	var duration = dur;//integer. number of seconds the tween takes
	var callback = cb;//string, opt. function to call when the tween is finished	
	var count=startVal;
	var intrv;
	var elm;
	var incrementVal;
	
	var INTERVAL_VALUE = 100;//milliseconds
			
	if(typeof elmId == "string")
	{
		elm = document.getElementById(elmId);
	}
	else 
	{
		elm = elmId;
	}
	
	if(prop=="top" || prop=="right" || prop=="bottom" || prop=="left")
	{
		elm.style.position = "relative";
	}
	
	intrv = setInterval(runTween,INTERVAL_VALUE)
	
	function runTween()
	{		
		var intervalSecs = INTERVAL_VALUE/1000;
		var loopCount = duration/intervalSecs;		
		
		incrementVal = Math.abs(startVal - endVal) / loopCount;			
		elm.style[prop] = count + unitOfMeasure;
		if(endVal > startVal) 
		{
			count = count + incrementVal;
			if(count >= endVal) 
			{	
				haltTween();
			}
		}
		else 
		{
			count = count - incrementVal;
			if(count <= endVal) 
			{
				haltTween();
			}
		}		
	}
	function haltTween()
	{
		elm.style[prop] = endVal + unitOfMeasure;
		clearInterval(intrv);		
		if(callback)
		{
			try
			{
				eval(callback);	
			}
			catch(e)
			{
				throw("[SLATE DOM ERROR] tween could not perform callback.");	
			}
		}	
	}
}


