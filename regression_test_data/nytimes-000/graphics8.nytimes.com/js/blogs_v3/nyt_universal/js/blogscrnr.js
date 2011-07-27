/*
$Id: blogscrnr.js 70125 2011-06-15 17:06:03Z doj $
*/

var NYTD = window.NYTD || {};

NYTD.BlogsCRNR = Class.create({
	initialize: function() {
		this.postLinksAndOverflowPageLinks = new Array();
		this.postLinks = new Array();
		this.postPermalinks = new Array();
	},
	
	setPostData: function(postLink, overflowPageLink, postPermalink) {
		this.postLinks.push('"' + postLink + '"');
		this.postLinksAndOverflowPageLinks[postLink] = overflowPageLink;
		this.postPermalinks[postLink] = postPermalink;
	},
	
	getPostLinksJoined: function() {
		this.postLinks = this.postLinks.uniq();
        var num_links = this.postLinks.length;
        if (num_links > 24) {
            this.postLinks = this.postLinks.slice(0,25);
        }
		return this.postLinks.join(",");
	},

	getAJAXRequest: function() {
		var postLinks = NYTD.blogsCRNRObj.getPostLinksJoined();
		
		if(postLinks) { /* if all posts on the page are accepting comments in wordpress then postLinks is empty. */
			return 'http://'+document.domain+'/svc/community/V2/requestHandler?requestData={"userContentSummary":{"request":{"requestType":"UserContentSummary","url":[' + postLinks + ']}}}';
		}
		else {
			return false;
		}
	},
	
	go: function() {
		var communityRequest = NYTD.blogsCRNRObj.getAJAXRequest();
		
		if(!communityRequest) /* if request empty, do nothing. */
			return false;
		
		new Ajax.Request(communityRequest,{
			method: 'get',
			onSuccess: function(r) {
				try{
					var response = r.responseText.evalJSON();
					var requestResponse = response["userContentSummary"].response;
					var assets = requestResponse["UserContentSummary"]["assets"];
					/* 
					 * if there is only one post on blog page, JSON response will not have "assets"
					 * if there is more than one post on blog page, JSON response will have "assets"
					 * 
					 * */
					if(typeof assets == 'undefined') {
						assets = new Array();						
						assets.push(requestResponse.UserContentSummary);
					}

					assets.each(function(UserContentSummary) {

						var anchors = $$('.post-comment');
						var postLink = UserContentSummary.url;
						var commentCount = UserContentSummary.commentCount;
						var commentQuestion = UserContentSummary.commentQuestion;
						
						anchors.each(function(anchor) {
							var overflowPageLink = anchor.href;
							var cCol = true;
							var aColLi = anchor.up('li');
							if((typeof aColLi != 'undefined') && (aColLi.hasClassName('comment-link'))) {
								cCol = false;
							}
							else {
								var aColDiv = anchor.up('div');
								if((typeof aColDiv != 'undefined') && (aColDiv.hasClassName('comment-link'))) {
									cCol = false;
								}
							}
							
							if(overflowPageLink == NYTD.blogsCRNRObj.postLinksAndOverflowPageLinks[postLink]) {
								var commentText = '';
								
								if(cCol) {
									switch(commentCount) {
										case 0: 
											/* hide if zero comments */
											anchor.hide();
											break;
										default:
											commentText = commentCount;
											/* since we are removing comments word from ccol widgets, 
											 * adding a css class to show comment icon in background 
											 * */
											anchor.addClassName("comments").removeClassName("hide");
											break;
									}
								}
								else {
									switch(commentCount) {
										case 0:
											commentText = 'Add a comment';
											if(typeof aColLi != 'undefined'){
												if(anchor.hasClassName('remove-if-dealbook')) {
													anchor.up('li').remove();
												}
												else {
													anchor.removeClassName("hide");
												}
											}
											else if(typeof aColDiv != 'undefined') {
												anchor.up('div').remove();
											}
											break;
										case 1:
											commentText = '1 Comment';
											anchor.removeClassName("hide");
											break;
										default:
											commentText = commentCount + ' Comments';
											anchor.removeClassName("hide");
											break;
									}
								}
								anchor.update(commentText);
							}
						});
					});
				}
				catch(error) {
					if(typeof window.console != 'undefined') console.log(error);
				}
			},
			onFailure: function(r) {
				NYTD.blogsCRNRObj.failed();
				return false;
			}
		});
	},
	
	failed: function() {
		if($('readersComments')) {
			$('readersComments').hide();
		}
		$$('li.comment-link').invoke('hide');
		$$('a.post-comment').invoke('hide');
	}
});

/* Not doing dom:loaded. had issues with IE 6/7. Now using window onload. */
NYTD.blogsCRNRObj = new NYTD.BlogsCRNR();
Event.observe(window, 'load', function() {
    var crnr = NYTD.blogsCRNRObj;
	crnr.go();
});
