function cleanWhitespace(node) {
notWhitespace = /\S/;
for (var x = 0; x < node.childNodes.length; x++) {
var childNode = node.childNodes[x]
if ((childNode.nodeType == 3)&&(!notWhitespace.test(childNode.nodeValue))) {
// that is, if it's a whitespace text node
node.removeChild(node.childNodes[x])
x--
}
if (childNode.nodeType == 1) {
// elements can have text child nodes of their own
cleanWhitespace(childNode)
}
}
}



function switchClass(objectToChange,oldClass,newClass)
{
		objectToChange.className=objectToChange.className.replace(new RegExp(oldClass), newClass);
}

function textLinkUtil()
{
	if(!location.href.match("no_ads")){
		var textlinkDIVref = document.getElementById('textlinkWrapper');
		cleanWhitespace(textlinkDIVref);
		var textlinkLIcoll = textlinkDIVref.getElementsByTagName('li');
			
		if(textlinkLIcoll.length > 0)
		{
			switchClass(textlinkDIVref,'noTextLinks','hasTextLinks')
			if(document.getElementById('clientTextLinkWrapper'))
			{
				cTextLinkWrap = document.getElementById('clientTextLinkWrapper');
				switchClass(cTextLinkWrap,'noTextLinks','hasTextLinks')
			}
			if(document.getElementById('slug_featured_links')){
				document.getElementById('slug_featured_links').style.display = 'block';
			}
			for(var i=0;i<textlinkLIcoll.length;i++)
			{	
				if(textlinkLIcoll[i].childNodes.length > 0)
				{
				var lineLength = (textlinkLIcoll[i].childNodes.length);
				var randomLine=Math.floor(Math.random()*lineLength)
				var winner = textlinkLIcoll[i].childNodes[randomLine];
					winner.style.display = 'inline';
					if(winner.getAttribute('trackingpixel'))
					{
						var imgPix = document.createElement('img');
						_ordNum = winner.getAttribute('trackingpixel');
						_ordPix = Math.floor(Math.random() * 10000000000000);
						trackPix = _ordNum.replace(/\%n/gi, _ordPix);
						imgPix.src = trackPix;
						imgPix.width = 1;
						imgPix.height = 1;
						textlinkDIVref.appendChild(imgPix)
					}
				}
			}
		}
	}
}

textLinkUtil();
