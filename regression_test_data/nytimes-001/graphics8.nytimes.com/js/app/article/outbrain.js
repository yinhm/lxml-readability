/*
 * $Id: outbrain.js 64459 2011-04-11 12:43:55Z gopi_borra $
 * (c) 2006-2011 The New York Times Company
 */

var OB_permalink= window.location.href.split("?")[0] + "?pagewanted=all";
var OB_Template="nytimes";
var OB_widgetId= 'AR_1';
var OB_langJS ='http://widgets.outbrain.com/lang_en.js';
 
 if ( typeof(OB_Script)!='undefined' ){
   OutbrainStart();
 } else {
   var OB_Script = true;
   NYTD.require("http://widgets.outbrain.com/outbrainWidget.js");
 }