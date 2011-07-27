(function(){
    var getQueryParam = function(name) {
        var results, expression = "[\\?&]"+name+"=([^&#]*)";
        if (results = window.location.href.match(expression)) {
            return results[1];
        }
        return false;
    }

    var utm_medium, q, params = {};

    if (document.location)
        params.location = document.location;
    if (document.referrer)
        params.referer = document.referrer;
    if (utm_medium = getQueryParam('utm_medium'))
        params.utm_medium = utm_medium;
    if ((typeof vertical != "undefined") && vertical)
        params.vertical = vertical;
    if (q = getQueryParam('q'))
        params.q = q;
        
    if (window.post && post) {
        params.post_id = post.id;
        params.post_author = (post.author instanceof Array) ? 
            post.author.join('|') : post.author;
        params.post_author_ids = post.author_ids;
    }

    var uri = '/track.gif?rand=' + Math.random();
    for (var k in params) {
        uri += '&' + k + '=' + encodeURIComponent(params[k]);
    }
    document.write('<img src="'+uri+'" />');
}());
