function slate_insert_comment_count(url, element, fullText) {
    //console.log(url);
    if (url.substring(0,1) == '/') {
        url = slate_public_url + url;
    }
    url = escape(url);
    var request = 'http://api.echoenabled.com/v1/count?q=childrenof%3A' + url + '*+type%3Acomment+-source%3ATwitter+sortOrder%3AreverseChronological+state%3AUntouched,ModeratorApproved+children%3A3&appkey=dev.slate.com&callback=?';
    $.getJSON(request, function(data, status, xhr) {
        var count = (data.count) ? data.count : 0;
        if (fullText) {
            if (count > 0) {
                if (count == 1) {
                    $(element).html("<span>1</span> Comment");
                } else {
                    $(element).html("<span>" + count + "</span> Comments");
                }
            } else {
                $(element).html("<br/> Comment");
            }
        } else {
            if (count > 0) {
                $(element).text(count);
            } else {
                $(element).text('0');
            }
        }
    });
}

function slatest_insert_twitter_count(url, element, fullText) {
    if (url.substring(0,1) == '/') {
        url = slate_public_url + url;
    }
    url = escape(url);
    var request = 'http://api.echoenabled.com/v1/count?q=childrenof%3A' + url + ' source%3ATwitter&appkey=dev.slate.com&callback=?';
    //console.log(request);
    $.getJSON(request, function(data, status, xhr) {
        var count = (data.count) ? data.count : 0;
        if (fullText) {
            if (count > 0) {
                if (count == 1) {
                    $(element).html("<span>1</span> Tweet");
                } else {
                    $(element).html("<span>" + count + "</span> Tweets");
                }
            } else {
                $(element).html("<br/> Tweet");
            }
        } else {
            $(element).text(count);
        }
    }); 
}

function slatest_insert_facebook_count(url, element, fullText) {
    if (url.substring(0,1) == '/') {
        url = slate_public_url + url;
    }
    url = escape(url);
    var request = 'http://graph.facebook.com/' + url + '?callback=?';
    //console.log(request);
    $.getJSON(request, function(data, status, xhr) {
        /*console.log(data);*/
        var count = (data.shares) ? data.shares : 0;
        if (fullText) {
            if (count > 0) {
                if (count == 1) {
                    $(element).html("<span>1</span> Like");
                } else {
                    $(element).html("<span>" + count + "</span> Likes"); 
                }
            } else {
                $(element).html("<br/> Like"); 
            }
        } else {
            $(element).text(count);
        }
    }); 
}

function fbs_click(url, t) {
    if (url.substring(0,1) == '/') {
        url = slate_public_url + url;
    }
    url = escape(url);
    t = escape(t);
    window.open('http://www.facebook.com/sharer.php?u='+encodeURIComponent(url)+'&t='+encodeURIComponent(t),'sharer','toolbar=0,status=0,width=626,height=436');
    return false;
}

function twt_click(url, t) {
    if (url.substring(0,1) == '/') {
        url = slate_public_url + url;
    }
    url = escape(url);      
    t = escape(t);
    
    // Jsonp calls cannot use window.open, so we open an empty window first as a workaround.
    twindow = window.open("", "twitter", 'toolbar=0,status=0,width=626,height=436');
    $.getJSON('http://api.bitly.com/v3/shorten?longurl=' + url + '&login=slate&apiKey=R_595d1e9a24a47c4615283fd74d9d8fda&callback=?', function(data) {      
        if (data.data.url != undefined) {
            url = escape(data.data.url);
        }
        twindow.location = 'http://twitter.com/intent/tweet?text=' + t + '&url=' + url + '&via=Slatest';
    });
     
    return false;
}



$(document).ready(function() {
    // Don't run Echo in Edit mode
    //console.log(typeof(CQ));
    if (typeof(CQ) == "undefined") {
        $(".slst-popular-menu a").click(function () {
            $(".slst-popular").removeClass("slst-popular-mode-read").removeClass("slst-popular-mode-shared");
            var base_class = "";
            if ($(this).hasClass("slst-popular-menu-link-read")) {
                base_class = "slst-popular-mode-read";
            } else if ($(this).hasClass("slst-popular-menu-link-shared")) {
                base_class = "slst-popular-mode-shared";
            }
            
            //console.log(base_class);
            $(".slst-popular").addClass(base_class);
            
            return false;
        });
 
        $(".slb-rrw-mps-menu a").click(function () {
            $(".slb-rrw-mps-widget").removeClass("slb-rrw-mps-mode-read").removeClass("slb-rrw-mps-mode-shared");
            var base_class = "";
            if ($(this).hasClass("slb-rrw-mps-menu-link-mr")) {
                base_class = "slb-rrw-mps-mode-read";
                $('.slb-rrw-mps-mr-indica').css('display','block');
                $('.slb-rrw-mps-ms-indica').css('display','none');
            } else if ($(this).hasClass("slb-rrw-mps-menu-link-ms")) {
                base_class = "slb-rrw-mps-mode-shared";
                $('.slb-rrw-mps-mr-indica').css('display','none');
                $('.slb-rrw-mps-ms-indica').css('display','block');
            }
            
            //console.log(base_class);
            $(".slb-rrw-mps-widget").addClass(base_class);
            
            return false;
        });
        
        // Most Shared and Most Read Box
        var read_elm = document.getElementById("slst-read-list");       
        $.getJSON('http://synd.slate.com/trending.json?callback=?', function(data) {
            $.each(data, function(index, item) {
                $(read_elm).html($(read_elm).html() + most_popular_render(item.link, item.title, item.dek, item.author, item.pubDate));
            });
        });

        var shared_elm = document.getElementById("slst-shared-list");
        $.getJSON('http://synd.slate.com/shared.json?callback=?', function(data) {
            $.each(data, function(index, item) {
                $(shared_elm).html($(shared_elm).html() + most_popular_render(item.link, item.title, item.dek, item.author, item.pubDate));
            });
        });
        
        function parseISO8601(dateStringInRange) {
            var isoExp = /^\s*(\d{4})-(\d\d)-(\d\d)T.*$/,
                date = new Date(NaN), month,
                parts = isoExp.exec(dateStringInRange);

            if(parts) {
                month = +parts[2];
                date.setFullYear(parts[1], month - 1, parts[3]);
                if(month != date.getMonth() + 1) {
                    date.setTime(NaN);
                }   
             }
            return date;
        }
        
        function most_popular_render(url, title, dek, author, date) {
            months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
            d = parseISO8601(date);
            datestring = months[d.getMonth()] + " " + d.getDate() + ", " + d.getFullYear();
            // Add data.item.data.object.content to this line once it includes the correct data
            return '<li><h3><a class="slst-popular-link" href="' + url + '">' + title + '</a></h3><p class="slst-popular-dek">' + dek + '</p><p class="slst-popular-byline">By ' + author + '<span class="slst-popular-dateline"> | ' + datestring + '</span></p></li>';            
        }
        
        Echo.Broadcast.subscribe("Stream.Item.onRender", function(topic, data, contextId) {
            if (data.target == shared_elm || data.target == read_elm) {
                //console.log(data.item.data);              
                elm = data.item.target;
                $(elm).html(most_popular_render(data.item.data.object.id, data.item.data.object.title, '', data.item.data.actor.title, data.item.data.object.published))
            }
            
            $('.slst-popular .echo-stream-more').detach();
        });
    }
});

