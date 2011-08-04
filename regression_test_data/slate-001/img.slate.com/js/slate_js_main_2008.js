//OpenFlash to be phased out.  Use renderSwf(below) instead. 
function OpenFlash(flashfile, width, height, flashVars) {document.write("<object classid='clsid:d27cdb6e-ae6d-11cf-96b8-444553540000' codebase='http://download.macromedia.com/pub/shockwave/cabs/flash/swflash.cab#version=9,0,0,0' width='" + width + "' height='" + height + "'><param name='allowScriptAccess' value='sameDomain' /><param name='allowFullScreen' value='false' /><param name='movie' value='" + flashfile + "' /><param name='flashVars' value='" + flashVars + "' /><param name='loop' value='false' /><param name='quality' value='high' /><param name='wmode' value='transparent' /><param name='bgcolor' value='#ffffff' /><embed src='" + flashfile + "' flashVars='"+flashVars+"' loop='false' quality='high' wmode='transparent' bgcolor='#ffffff' width='" + width + "' height='" + height + "' name='Test' allowScriptAccess='sameDomain' allowFullScreen='false' type='application/x-shockwave-flash' pluginspage='http://www.macromedia.com/go/getflashplayer'></embed></object>"); }

function OpenOmnitureFlash(VideoID,PlayerID,Width,Height,AdServer,AutoStart) {	document.write("<object classid='clsid:d27cdb6e-ae6d-11cf-96b8-444553540000' codebase='http://fpdownload.macromedia.com/pub/shockwave/cabs/flash/swflash.cab#version=9,0,0,0' width='" + Width + "' height='" + Height + "' id='omniturePlayer' align='middle'><param name='allowScriptAccess' value='always' /><param name='movie' value='http://www.slate.com/video/omniturePlayer.swf?actionSourcePath=http://www.slate.com/video/&adServerURL=" + AdServer + "&videoId=" + VideoID + "&videoRef=null&lineupId=null&playerTag=null&autoStart=" + AutoStart + "&pwidth=" + Width + "&pheight=" + Height + "&playerId=" + PlayerID + "&flashId=omniturePlayer' /><param name='quality' value='high' /><param name='bgcolor' value='#FFFFFF' /><embed src='http://www.slate.com/video/omniturePlayer.swf?actionSourcePath=http://www.slate.com/video/&adServerURL=" + AdServer + "&videoId=" + VideoID + "&videoRef=null&lineupId=null&playerTag=null&autoStart=" + AutoStart + "&pwidth=" + Width + "&pheight=" + Height + "&playerId=" + PlayerID + "&flashId=omniturePlayer' quality='high' bgcolor='#FFFFFF' width='" + Width + "' height='" + Height + "' name='omniturePlayer' align='middle' allowScriptAccess='always' type='application/x-shockwave-flash' pluginspage='http://www.macromedia.com/go/getflashplayer' /></object>"); 
}
function insertAudioPlayer(soundfile, extFile) { document.write('<object width="244" height="46" align="middle" id="audioplayer" codebase="http://fpdownload.macromedia.com/pub/shockwave/cabs/flash/swflash.cab#version=6,0,0,0" classid="clsid:d27cdb6e-ae6d-11cf-96b8-444553540000"><param value="sameDomain" name="allowScriptAccess"></param><param value="http://www.slate.com/apps/audioplayer.swf?soundfile='+soundfile+'&externalFile='+extFile+'" name="movie"></param><param value="high" name="quality"></param><param value="#ffffff" name="bgcolor"></param><embed width="244" height="46" align="middle" pluginspage="http://www.macromedia.com/go/getflashplayer" type="application/x-shockwave-flash" allowscriptaccess="sameDomain" name="audioplayer" bgcolor="#ffffff" quality="high" src="http://www.slate.com/apps/audioplayer.swf?soundfile='+soundfile+'&externalFile='+extFile+'"></embed></object>') 
}
function OpenSurroundVideo(file, width, height, filepath){if (width == null || width == "")width="320"; if (height==null || height =="")height="240";  myvideo = "<object classid='clsid:928626A3-6B98-11CF-90B4-00AA00A4011F' type='application/x-oleobject' id='Surround1'" + " codebase='" + filepath+ "apps/svj/MSSurVid.cab#Version=1,2,0,20' width='" +width + "' height='" + height + "'>" + "<param name='SurroundRect' value='0,0,320,240' /><param name='Image' value='"+file+"'></param></object>";  document.write(myvideo); 
}
function OpenWindowsMedia(file){document.write("<embed type='application/x-mplayer2' name='MediaPlayer' autostart='true'  src='" + file + "'></embed>"); 
}
function OpenQuickTime(file, width, height){document.write("<embed PLUGINSPAGE='http:/" + "/www.apple.com/quicktime/download/' src='"+ file +"' width='"+width+"' height='"+height+"'></embed>"); }
// Above are functions for activex components

//handles page refreshes
var timeout; 
function refreshPage(seconds)
{
	var d = new Date();
	if(d.getDay() % 6 == 0)//weekend vals are 0 (Sunday) and 6 (Saturday)
	{
		seconds *= 3;
	}		
	if(window.location.href.indexOf("/id/") < 0)
	{
	window.timeout = window.setTimeout(refresh, seconds*1000);		
	}
	function refresh()
	{
		window.location.replace('?reload=true');
	}
}
function updateRefresh(seconds)
{
	window.clearTimeout(window.timeout);
	refreshPage(seconds);
}

function SlatePopup(div) { var win = window.open("","win","directories=no,height=400,width=550,menubar=no,resizeable=no,scrollbars=no,status=no,toolbar=no"); win.document.write("<html><head><title>Slate Popup</title><link rel=\"stylesheet\" type=\"text/css\" href=\"/css/popups.css\" /></head><body></body></html>"); win.document.body.innerHTML = div.innerHTML; win.document.close(); win.focus(); return;
}
function toolAction(action, id, tocid) {var title; var windowParam; if (id==''){var url = window.location.href; var idPos = url.indexOf("id="); if (idPos != -1){var ampPos = url.indexOf("&"); if (ampPos != -1)id = url.substring(idPos+3,ampPos); else id = url.substr(idPos+3); }}var URLParam = "?action="+action+"&id="+id; if (id=='toc')URLParam += "&tocid="+tocid; switch (action) {case 'print':title=''; windowParam = 'toolbar=no,location=no,directories=no,menubar=yes,status=no,resizable=yes,scrollbars=yes,'; window.open("/toolbar.aspx"+URLParam, title, windowParam); break; case 'email':title='Email'; windowParam = 'toolbar=no,location=no,directories=no,menubar=no,status=no,resizable=yes,scrollbars=no,width=490,height=470'; window.open("/toolbar.aspx"+URLParam, title, windowParam); break; }
}
function showHideSidebar(){if(document.all)var iWidth = document.body.clientWidth; document.all.sidebarshell.style.display = (iWidth > 913 ? '' : 'none'); document.all.sidebarshell.style.height = document.body.scrollHeight - 1; 
}
function LoadIframe(el){var n = el.name; var h = document.frames(n).document.body.scrollHeight; el.height = h; window.focus(); 
}
// Used for most read, e-mailed
function clearMostTabs() {
	for(k=1;k<=2;k++) {
		document.getElementById("most_link"+k).className="mostread_inactive";		document.getElementById("most_read_"+k).style.display="none";	
	} 
}
function selectMostTab(id) {
	clearMostTabs();	
	document.getElementById("most_link"+id).className="mostread_active";	document.getElementById("most_read_"+id).style.display="block"; 
}
// Image preload script
var myimages=new Array(); function preloadimages() {  for (i=0;i<preloadimages.arguments.length;i++)  {    myimages[i]=new Image();    myimages[i].src=preloadimages.arguments[i];  } } preloadimages("http://img.slate.com/images/redesign2008/slate_logo.gif","http://img.slate.com/images/redesign2008/flyoutnotch.gif","http://img.slate.com/images/redesign2008/left_whitemaroon.gif","http://img.slate.com/images/redesign2008/left_maroonmaroon.gif","http://img.slate.com/images/redesign2008/left_maroonwhite.gif","http://img.slate.com/images/redesign2008/middle_whitemaroon.gif","http://img.slate.com/images/redesign2008/middle_maroonwhite.gif","http://img.slate.com/images/redesign2008/middle_maroonmaroon.gif","http://img.slate.com/images/redesign2008/right_maroonwhite.gif","http://img.slate.com/images/redesign2008/right_whitewhite.gif");
// Flyout menus
var ActiveMenu = null;
var closeMenu;
var recIsOpen = false;
function setBizBoxFlyout(num) {
	var span = document.getElementById("bizbox_latest_header_"+num);
  document.getElementById("bizbox_latest_link_"+num).href = bizbox_latest_href;
  if(span.textContent)
  {
	  span.textContent = bizbox_latest_title;  
  }
  else
  {
	  span.innerText = bizbox_latest_title;  
  }
}
function showMenu(menuNum) {	clearTimeout(closeMenu);	var whichMenu = parseInt(menuNum);	if (ActiveMenu != null) {	hideMenu(); 	}	if (readCookie("slateflyout") != "off") { document.getElementById("flyout_container").innerHTML = flyoutArray[whichMenu - 1]; document.getElementById("flyout_container").style.display = "block"; } 	var highlightLink = document.getElementById("menuF" + whichMenu);	highlightLink.style.color="#FF0";	ActiveMenu = whichMenu; /*setBizBoxFlyout(whichMenu);*/ }
function hideMenu() {
	document.getElementById("flyout_container").style.display="none"; var highlightLink = document.getElementById("menuF" + ActiveMenu); highlightLink.style.color="#FFF"; ActiveMenu = null;}
	
// Turn off flyouts
function flyoutTurnoff() { var date = new Date(); date.setTime(date.getTime()+(10000*24*60*60*1000)); document.cookie = "slateflyout=off; expires=" + date.toGMTString() + "; path=/"; window.location.reload(); }
function flyoutTurnon() { var date = new Date(); date.setTime(date.getTime()+(-1*24*60*60*1000)); document.cookie = "slateflyout=off; expires=" + date.toGMTString() + "; path=/"; window.location.reload(); }
function flyoutSwitch() { if (readCookie("slateflyout") != "off") { document.write("<div class='flyout_toggler'><a class='flyout_switch' href='javascript:flyoutTurnoff()'>Disable Flyout</a><a href='http://www.slate.com/id/2147826/'><img src='http://img.slate.com/images/redesign/disableflyout_infocircle.gif' width='13' height='13' alt='What does disabling the flyout do?' /></a></div>"); } else { document.write("<div class='flyout_toggler'><a class='flyout_switch' href='javascript:flyoutTurnon()'>Enable Flyout</a><a href='http://www.slate.com/id/2147826/'><img src='http://img.slate.com/images/redesign/disableflyout_infocircle.gif' width='13' height='13' alt='What does disabling the flyout do?' /></a></div>"); } }
function readCookie(name) { var nameEQ = name + "="; var ca = document.cookie.split(';'); for(var i=0;i < ca.length;i++) { var c = ca[i]; while (c.charAt(0)==' ') c = c.substring(1,c.length); if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length); } return null; }

// Open "recommend" link
function ToolbarRecommend(whichRec) {
	if (recIsOpen == false) {		document.getElementById(whichRec).style.display="block";		recIsOpen = true;	} else {		document.getElementById(whichRec).style.display="none";		recIsOpen = false;	}
}
function closeRec(whichRec) {
	document.getElementById(whichRec).style.display="none";	recIsOpen = false;
}

// Toolbar mouseover
function ToolbarMouseOver(whichMenu, rootpath) {
	var navImage = whichMenu + "_icon";	var navAnchor = whichMenu + "_link";	document.images[navImage].src = (rootpath + "images/toolbox_images/" + whichMenu + "_roll.gif");	document.getElementById(navAnchor).style.color = "#FF0";}
function ToolbarMouseOut(whichMenu, rootpath) {
	var navImage = whichMenu + "_icon";	var navAnchor = whichMenu + "_link";	document.images[navImage].src = (rootpath + "images/toolbox_images/" + whichMenu + ".gif");
	document.getElementById(navAnchor).style.color = "#FFF";}
	
// Multipart navigation functions
var MultipartHeadlines = new Array();	var CurrentEntry = null;
function PopulateMultipartArray(ArrayIndex, Headline, FromByline, ToByline, PubDate, thisHeadline) {	var whichElement = parseInt(ArrayIndex);		MultipartHeadlines[whichElement] = [Headline,FromByline,ToByline,PubDate];	if (thisHeadline == '1')		CurrentEntry = whichElement;} function MultipartMouseOver(whichSwap, TopBottomSwitch) {	whichElement = parseInt(whichSwap);	TopOrBottom = "multipart" + TopBottomSwitch;	if (MultipartHeadlines[whichElement][2] == 'null') {	document.getElementById(TopOrBottom).innerHTML = ("<h2>" + MultipartHeadlines[whichElement][0] + "</h2><span class='multipart_byline'>" + MultipartHeadlines[whichElement][1] + "</span><span class='multipart_date'>Posted " + MultipartHeadlines[whichElement][3] + "</span>");	} else {		document.getElementById(TopOrBottom).innerHTML = ("<h2>" + MultipartHeadlines[whichElement][0] + "</h2><span class='multipart_byline'>" + MultipartHeadlines[whichElement][1] + "<br />" + MultipartHeadlines[whichElement][2] + "</span><span class='multipart_date'>Posted " + MultipartHeadlines[whichElement][3] + "</span>");	}}
function MultipartMouseOut(TopBottomSwitch) {	TopOrBottom = "multipart" + TopBottomSwitch;	if (MultipartHeadlines[CurrentEntry][2] == 'null') {	document.getElementById(TopOrBottom).innerHTML = ("<h2>" + MultipartHeadlines[CurrentEntry][0] + "</h2><span class='multipart_byline'>" + MultipartHeadlines[CurrentEntry][1] + "</span><span class='multipart_date'>Posted " + MultipartHeadlines[CurrentEntry][3] + "</span>");	} else {		document.getElementById(TopOrBottom).innerHTML = ("<h2>" + MultipartHeadlines[CurrentEntry][0] + "</h2><span class='multipart_byline'>" + MultipartHeadlines[CurrentEntry][1] + "<br />" + MultipartHeadlines[CurrentEntry][2] + "</span><span class='multipart_date'>Posted " + MultipartHeadlines[CurrentEntry][3] + "</span>");	} }

var tapOneCount = 0;
var tabStates = {todaysMedia:-1,tap1:-1,tap3:-1,tis:-1};
var hpCookieData = (readCookie("slateHPState") != null) ? readCookie("slateHPState").split(",") : null;
var tap3Html = new Array();
var tap3DisplayCount = 4;
var tapThreeIndex;
var tapOneIndex = 1;
var mediaPlayerOpen = 0;
//var todaysMediaRandomVar = Math.floor(Math.random() * 5) + 1;

function randomizeTopPromo(promoCount) {
	var whichPromo = Math.floor(Math.random() * promoCount) + 1;
	document.getElementById("toc_top_promo_1").style.display = "none";
	document.getElementById("toc_top_promo_" + whichPromo).style.display = "block";
}

//called from TOC.xsl
function changeTapOne(index) {	
	var controllerDivs;
	var className;
	var classNameOff;
	var regEx;
	
	for(var i=1; i<=tapOneCount; i++)
	{
		document.getElementById("tap1_"+i).style.display="none";
	}
	document.getElementById("tap1_"+index).style.display="block";
	
	controllerDivs = document.getElementById("tap1_tabs").getElementsByTagName("div");	
	for(var i=0; i<controllerDivs.length; i++)
	{
		className = controllerDivs[i].className;
		classNameOff = className.replace("_on","_off")
		controllerDivs[i].className = classNameOff;
		if(className.indexOf("segue")>=0)
		{	
			if(i+2==controllerDivs.length)
			{
				regEx = /_[AB]/i;
				controllerDivs[i].className = classNameOff.replace(regEx,"_C");
			}
			else
			{
				regEx = /_[BC]/i;
				controllerDivs[i].className = classNameOff.replace(regEx,"_A");
			}
		}
	}
	//prev
	className = controllerDivs[index + (index-2)].className;
	controllerDivs[index + (index-2)].className = className.replace("_off","_on");
	if(className.indexOf("segue")>=0)
	{	
		regEx = /_[AC]/i;
		controllerDivs[index + (index-2)].className = className.replace(regEx,"_B");
	}
	//cur
	className = controllerDivs[index + (index-1)].className;
	controllerDivs[index + (index-1)].className = className.replace("_off","_on");
	//next
	className = controllerDivs[index*2].className;
	controllerDivs[index*2].className = className.replace("_off","_on");
	if(index==tapOneCount)
	{
		regEx = /_[AB]/i;
		className = controllerDivs[index*2].className;
		controllerDivs[index*2].className = className.replace(regEx,"_C");
		tapOneIndex = index;
	}
}
function initTapThree()
{
	var maxItems = 4;
	var tap3Mask = document.getElementById("tap3_mask");
	var tap3Tray = document.getElementById("tap3_tray");
	var tap3Items = tap3Tray.getElementsByTagName("li");
	var tap3Item = new Object();
		tap3Item.elm = tap3Tray.getElementsByTagName("li")[0];
		tap3Item.width = parseInt(SlateDom.getCurrentStyle(tap3Item.elm,"width"));
		tap3Item.height = (isNaN(SlateDom.getCurrentStyle(tap3Item.elm,"height")))?"auto":SlateDom.getCurrentStyle(tap3Item.elm,"height");
		tap3Item.lMargin = (parseInt(SlateDom.getCurrentStyle(tap3Item.elm,"margin-left")))?parseInt(SlateDom.getCurrentStyle(tap3Item.elm,"margin-left")):parseInt(SlateDom.getCurrentStyle(tap3Item.elm,"marginLeft"));
		
	with(tap3Mask.style)
	{
		width = ((tap3Item.width + tap3Item.lMargin * 2) * maxItems) + "px";
		height = tap3Item.height;
	}
	with(tap3Tray.style)
	{
		width = ((tap3Item.width + tap3Item.lMargin * 2) * tap3Items.length) + "px";
		height = tap3Item.height;
		left = "0px"
	}
	var tap3Lefts = new Array();
	var maskWidth = parseInt(tap3Mask.style.width);
	var trayWidth = parseInt(tap3Tray.style.width);
	var failInt = Math.floor(trayWidth/maskWidth);
	for (var i=0; i<failInt; i++)
	{
		tap3Lefts.push((-(maskWidth*i))+"px");
	}
	tap3Tray.style.left = tap3Lefts[parseInt(Math.random()*tap3Lefts.length)];
}

function moveTap3(dir)
{
	var tap3Tray = document.getElementById("tap3_tray");
	var pos = parseInt(tap3Tray.style.left);
	var trayWidth = parseInt(tap3Tray.style.width);
	var maskWidth = parseInt(document.getElementById("tap3_mask").style.width);
	if(dir=="left")
	{
		if(pos - maskWidth < maskWidth - trayWidth)
		{
			tap3Tray.style.left = 0
		}
		else
		{
			tap3Tray.style.left = (pos - maskWidth) + "px";
		}
	}
	if(dir=="right")
	{
		if(pos + maskWidth > 0)
		{			
			tap3Tray.style.left = maskWidth - trayWidth + "px";
		}
		else
		{
			tap3Tray.style.left = (pos + maskWidth) + "px";
			
		}
	}
}

function showDaysArticles(whichUL) {
	var ULswitcher = document.getElementById("day" + whichUL);
	var arrowSwitcher = document.getElementById("day_arrow_" + whichUL);
	if (ULswitcher.style.display == "none") {
		ULswitcher.style.display = "block";
		arrowSwitcher.src = "http://img.slate.com/images/redesign2008/daily_arrow_down.gif";
	} else {
		ULswitcher.style.display = "none";
		arrowSwitcher.src = "http://img.slate.com/images/redesign2008/daily_arrow_rt.gif";
	}
} 
/*function changeMediaPlayer(whichOne) {
	if (whichOne == 5)
		whichOne = 4;
  window.tabStates.todaysMedia = whichOne;
	whichOne = whichOne.toString()
	if (mediaPlayerOpen != whichOne) {
		document.getElementById("toc_media_" + whichOne).style.visibility="visible";
		document.getElementById("med_" + whichOne).className="med_active";
		if (mediaPlayerOpen != 0 ) {
			document.getElementById("toc_media_" + mediaPlayerOpen).style.visibility="hidden";
			document.getElementById("med_" + mediaPlayerOpen).className="med_inactive";
		}
		mediaPlayerOpen = whichOne;
	}
}*/
function getTabRandom() {
	var i = "";
	var j = Math.floor(Math.random() * 4) + 1;
	switch (j) {
		case 1: i="blogroll_tab";break;
		default:i="today_tab";
	}
	return i;
}
function switchArticleContainer(whichOne) {
	window.tabStates.tis = whichOne;
	document.getElementById(whichOne).className = "ab_active";
	if (whichOne == "today_tab") {
		document.getElementById("blogroll_tab").className = "ab_inactive";
		document.getElementById("blogs_container").style.display = "none";
		document.getElementById("today_in_slate").style.display = "block";
	} else {
		document.getElementById("today_tab").className = "ab_inactive";
		document.getElementById("blogs_container").style.display = "block";
		document.getElementById("today_in_slate").style.display = "none";		
	}
}
//Slate Search
  var searchInputCleared = false;
	var searchEngine;
	var searchImgs={};//set in html40/CascadingMenu.xsl
	
  function clearSearchInput() { 
    if (!searchInputCleared) { document.forms['site_search'].srch_text.value = ''; }
    searchInputCleared = true;
  }
  
  function initSearch(evt){
		var form,radio,cntr,opts,rads;		

		window.searchEngine = "slate";		
		form = document.forms["site_search"];
		radio = document.getElementById("srch_radio_opt_" + window.searchEngine);			
		cntr = document.getElementById("srch_options");		
		opts = cntr.getElementsByTagName("div");
		rads = cntr.getElementsByTagName("input");		

		for(var i=0; i<opts.length;i++)
		{		
			SlateDom.addListener(opts[i],"click",setSearch);
			SlateDom.addListener(rads[i],"click",setSearch);
			opts[i].style.cursor = "pointer";
		}
		SlateDom.dispatchEvent(radio,"click");	
  }
  
  function setSearch(evt){
		var cur = SlateDom.getTarget(evt);		
		if(cur.id.indexOf("srch_opt")>=0 && window.searchEngine == cur.id.substr(cur.id.lastIndexOf("opt_") + 4))
		{			
			submitSearch();
		}

		window.searchEngine = cur.id.substr(cur.id.lastIndexOf("opt_") + 4);
		document.getElementById("srch_radio_opt_" + window.searchEngine).checked = true;
		document.getElementById("srch_submit_img").src = searchImgs[window.searchEngine];		
  }

  function submitSearch() {
    var engine, action, form, input, qText;
    
    engine = window.searchEngine;   
    qText = document.forms["site_search"].srch_text.value;  
		form = document.createElement("form");
		document.body.appendChild(form);
    form.method = "GET";
    switch(engine)
    {
			case("slate"):				
		    form.action = getSearchAction();
				input = SlateDom.newInputElement("hidden","id","3944");
				form.appendChild(input);
				input = SlateDom.newInputElement("text","qt",qText)
				form.appendChild(input);
				break;
			case("msn"):
		    form.action = "http://www.bing.com/results.aspx";
				input = SlateDom.newInputElement("hidden","FORM","ESLATE");
				form.appendChild(input);
				input = SlateDom.newInputElement("hidden","q",qText);
				form.appendChild(input);
				break;
			default:
				throw("[ERROR] No search engine selected.");
    }
    form.submit();
    return false;
  }
  
  function getSearchAction()
  {
		var host = window.location.hostname;
		switch(host)
		{
			case("www.doonesbury.com"):
			case("cartoonbox.slate.com"):
			case("todayspictures.slate.com"):
				return "http://www.slate.com/default.aspx";
				break;
			default:
				//hardcoding default to fix slatest search bug where no shell components are rendered
				return "http://www.slate.com/default.aspx";
		}
  }
//End Slate Search

//renderSwf to replace OpenFlash
function renderSwf(file, width, height, flashVars, id, wmode, bgcolor, scriptAccess)
{
	if (file == undefined || width == undefined || height == undefined)
	{
		alert("A file, width, and height must be specified.");
		return false;
	}	
	if(file.indexOf(".swf") > -1)
	{
		alert("Please remove the .swf extension from the filename.");
		return false;
	}	
	if(id==undefined)
	{
		var id = "flashMovie";
	}
	if(wmode==undefined)
	{
		var wmode = "window";
	}
	if(bgcolor==undefined)
	{
		var bgcolor = "#ffffff";
	}
	if(scriptAccess==undefined)
	{
		var scriptAccess = "sameDomain";
	}
	if (AC_FL_RunContent == 0) {
		alert("This page requires AC_RunActiveContent.js.");
	} else {
		AC_FL_RunContent(
			'codebase', 'http://download.macromedia.com/pub/shockwave/cabs/flash/swflash.cab#version=9,0,0,0',
			'flashVars', flashVars,
			'width', width,
			'height', height,
			'src', file,
			'quality', 'high',
			'pluginspage', 'http://www.macromedia.com/go/getflashplayer',
			'align', 'middle',
			'play', 'true',
			'loop', 'true',
			'scale', 'showall',
			'wmode', wmode,
			'devicefont', 'false',
			'id', id,
			'bgcolor', bgcolor,
			'name', id,
			'menu', 'true',
			'allowFullScreen', 'false',
			'allowScriptAccess',scriptAccess,
			'movie', file,
			'salign', ''
			); //end AC code
	}
}

var adsOpen = new Array();

//called from the new player.  Right now this will just call the old showCompanion function, but would like to smoooth it out with JQuery at some point
function handleCompanion(bannerURL, clickThroughURL, primaryVideoID, action)
{
	if(action == "open")
	{
		showCompanion(0,251,80,bannerURL,clickThroughURL,"article_player_"+primaryVideoID,"article_ad_companion_"+primaryVideoID);
	}
	else
	{
		showCompanion(251,0,80,bannerURL,clickThroughURL,"article_player_"+primaryVideoID,"article_ad_companion_"+primaryVideoID);
	}
}

function showCompanion(startHeight, endHeight, speed, imgSrc, clickURL, targetId, divId, lbHeight) //speed = milliseconds for animation
{	
	if(startHeight==0 && adsOpen.length > 0)
	{
		removeAd(divId);
	}
	var count = 0;
	var intrv;
	var parentDiv = document.getElementById(targetId);
	var adDiv;

	if(document.getElementById(divId))
	{
		adDiv = document.getElementById(divId);
	}
	else
	{
		adDiv = document.createElement("div");	
		parentDiv.appendChild(adDiv);
	}
	with(adDiv)
	{
		id = divId;
		with(style)
		{
			height=startHeight+"px";
			overflow="hidden";
			position="relative";
			textAlign = "center";
		}
	}
	function adIsOpen(divId)//checks for open ad divs
	{
		for (var i=0; i<adsOpen.length; i++)
		{
			if (adsOpen[i]==divId)
			{
				return true;
			}				
		}
		return false;
	}	
	
	function removeAd(divId)
	{
		for (var i=0; i<adsOpen.length; i++)
		{
			if (adsOpen[i]==divId)
			{
				adsOpen.splice(i,1);
				break;
			}				
		}
	}		
	if(adIsOpen(divId))
	{		
		intrv = setInterval(collapseDiv,speed);
		count = parseInt(adDiv.style.height);
		removeAd(divId);
	}
	else
	{	
		appendAd();
		intrv = setInterval(expandDiv,speed);
		adsOpen.push(divId);
	}
	
	function expandDiv()
	{
		adDiv.style.height = count + "px";
		count += 10;
		var stopPoint = (lbHeight != undefined) ? lbHeight : endHeight;
		if(count >= stopPoint) clearInterval(intrv);
	}
	function collapseDiv()
	{
		adDiv.style.height = count + "px";
		count -= 10;
		if(parseInt(adDiv.style.height) <= 10) 
		{
			clearInterval(intrv);
			parentDiv.removeChild(document.getElementById(divId));
			if(targetId.indexOf("todays_media_player") >= 0)
			{
				document.getElementById('homepagePlayer').enableTabs();
			}
			/*if(imgSrc != undefined)//handle leave-behind
			{
				count = 0;
				intrv = setInterval(expandDiv,speed);
				adOpen = true;
			}*/
		}
	}
	
	function appendAd()
	{
		if(document.getElementById(divId + "_ad_link")) adDiv.removeChild(document.getElementById(divId + "_ad_link"));
		
		var imgAnc = document.createElement("a");
		imgAnc.id = divId + "_ad_link";
		imgAnc.href = clickURL;
		adDiv.appendChild(imgAnc);

		var adImg = document.createElement("img");
		adImg.style.margin = "0px";
		adImg.src = imgSrc;
		imgAnc.appendChild(adImg);
	}
}

function showOmniVars()
{
	var txt = "\nserver=" + s.server;
			txt += "\npageName=" + s.pageName;
			txt += "\nchannel=" + s.channel;
	
	for (var prop in s)
	{	
		if (typeof(s[prop]) != "function")
		{
			if(prop.indexOf("prop") == 0 || prop.indexOf("hier") == 0)
			{
				txt += "\n" + prop + "=" + s[prop];
			}
		}
	}
	alert(txt)
}


function createIpadAd(){
	var isipad = navigator.userAgent.match(/iPad/i) != null;
	if(isipad){  //check to see if user is browsing with iPad
		
		if (typeof(localStorage) == 'undefined' ){  //Check to see if localStorage is a feature
			alert('Your browser does not support HTML5 localStorage. Try upgrading.');
		} else {
			try {
				var key = localStorage.getItem("ipadAd");
				
				if (key == null){  //check to see if ad has not been closed
					ipadAdNode();
				}
			} catch (e){
				alert(e);
			}
		}			
	}
}
	
function ipadAdNode(){
	var adWrapper = $("<div />").attr({
		"id" : "ipadAdWrapper"
	});
	var bgWrapper = $("<div />").attr({
		"class" : "bgWrapper"
	});
	var adDiv = $("<div />").attr({
		"class" : "ipadAd"
	});
	var logoDiv = $("<div />").text("Slate").attr({
		"class" : "logo"
	});				
	var adTxt = $("<p />").html("Try <strong><em>Slate's</em> FREE</strong> iPad app.").attr({
		"class" : "text"
	});
	var adLink = $("<a />").text("DOWNLOAD FOR FREE").attr({
		"class" : "link",
		"href" : "http://itunes.apple.com/us/app/slate-magazine/id384914589?mt=8"
	});

	var innerWrapper = $("<div />").attr({
		"class" : "innerWrapper"
	});
	var touchDiv = $("<div />").attr({
		"class" : "touchAd"
	});
	var touchLink = $("<a />").html('Or try the "beta" version of <b>our touch-optimized website<b>.').attr({
		"class" : "link",
		"href" : "http://touch.slate.com"
	});
	var closeDiv = $("<div />").text("X").attr({
		"class" : "close"
	});
	var clearingDiv = $("<div />").attr({
		"class" : "clearing"
	});
	$("#main_body_wrapper").before(adWrapper);
		bgWrapper.appendTo(adWrapper);
			innerWrapper.appendTo(bgWrapper);	
				adDiv.appendTo(innerWrapper);	
	logoDiv.appendTo(adDiv);
	adTxt.appendTo(adDiv);
						adLink.appendTo(adTxt);	
				touchDiv.appendTo(innerWrapper);
					touchLink.appendTo(touchDiv);	
					closeDiv.appendTo(touchDiv);
				clearingDiv.appendTo(innerWrapper);
	
	//redirect on click of ad text
	adTxt.click(function(){
		$(location).attr("href", "http://itunes.apple.com/us/app/slate-magazine/id384914589?mt=8");
	});
	
	//fade out ad on close
	closeDiv.click(function(){
		$("#ipadAdWrapper").fadeOut();
		localStorage.setItem("ipadAd", "x"); //saves to the storage, "key", "value"
	});
	
	//$(".ipadAd").delay(1500).slideToggle();
}

function commentLoad(){
	var d = $("<div />");
	var p = $("<p />");
	
	d.attr({
		"id" : "load-comments-wrapper"
	});
	
	p.text("If comments do not automatically load, click here.").attr({
		"class" : "load-comments"
	}).appendTo(d);
	
	d.appendTo("#js_kit_cntr");
	
	$(".load-comments").click(function(){
		$(this).fadeOut();
		reloadComments();
	});
}

function reloadComments(){
	jQuery(document).ready(function() {
		var jskitscript = document.createElement('script');
		jskitscript.type='text/javascript';
		jskitscript.src='http://cdn.js-kit.com/scripts/comments.js';
		document.body.appendChild(jskitscript);
	});
}