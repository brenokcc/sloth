var cursor = document;
var testLoggerIdent = '';

function formatValue(value){
    if(value && value.length==10 && value.indexOf('-')==4){
        var tokens = value.split('-');
        if(tokens.length==3) return tokens[2]+'/'+tokens[1]+'/'+tokens[0];
    } return value;
}

function testlogger(command){
    if(LOG_TEST_ACTIONS) $.get('/app/dashboard/test_logger/?command='+testLoggerIdent+command);
}

function initTestLogger(element){
    if(!LOG_TEST_ACTIONS) return;
    $(element).find('.btn i.bi').click(function(){testlogger("self.click_icon('"+$(this).attr('class').replace('bi ', '').replace('bi-', '')+"')")});
    $(element).find('input, textarea').not('input[type=checkbox]').blur(function(){testlogger("self.enter('"+$(this).parent().find('label').html().trim().replace('*', '')+"', '"+formatValue($(this).val())+"')")});
    $(element).find('select').change(function(){testlogger("self.choose('"+$(this).parent().find('label').html().trim().replace('*', '')+"', '"+$(this).find('option:selected').html()+"')")});
    $(element).find('a:not(.btn):not(.nav-link):not(.menu-item):not(.menu-subitem):not(.search-menu-item)').click(function(){testlogger("self.click_link('"+$(this).text().replace("Loading...", "").trim()+"')")});
    $(element).find('a.nav-link').click(function(){testlogger("self.click_tab('"+$(this).find('.nav-link-text').text().trim()+"')")});
    $(element).find('a.menu-subitem').click(function(){testlogger("self.click_menu"+$(this).data("hierarchy")+"")});
    $(element).find('a.search-menu-item').click(function(){testlogger("self.search_menu('"+$(this).text().trim()+"')")});
    $(element).find('a.btn').click(function(){var label=$(this).text().trim(); if(label) testlogger("self.click_button('"+label+"')")});
    $(element).find('button').click(function(){var label=$(this).text().replace("Loading...", "").trim(); if(label) testlogger("self.click_button('"+label+"')")});
    $(element).find('input[type=checkbox]').click(function(){testlogger("self.check('"+$(this).parent().find('label').html().trim().replace('*', '')+"')")});
    $(element).find('btn i.bi').click(function(){testlogger("self.click_icon('"+$(this).attr('class').replace("bi ", "").replace("bi-", "")+"')")});
}

function fakeMouse(){
    if($("#fake-cursor").length==0) {
        var img = $('<img id="fake-cursor">');
        img.attr('id', "fake-cursor");
        img.attr('src', "/static/images/hand.png");
        img.css('position', 'absolute');
        img.css('top', '300px');
        img.css('left', '300px');
        img.css('z-index', '99999999');
        img.appendTo(document.body);
    }
}

function fakeType(el, string, index){
      var val = string.substr(0, index + 1);
      el.val(val);
      if (index < string.length) {
        setTimeout(function(){ fakeType(el, string, index + 1); }, Math.random() * 200);
      }
      if(index==string.length-1){
          var daterangepicker = el.data('daterangepicker');
          if(daterangepicker) daterangepicker.hide();
      }
}

function showFakeMouse(force){
    var top = $(document).getCookie('mouse-top') || 0;
    var left = $(document).getCookie('mouse-left') || 0;
    if($('#fake-cursor').length==0) $('body').append(
        '<img id="fake-cursor" style="display:none;position:absolute;z-index:9999999;top:'+top+';left:'+left+'"/>'
    );
    $("#fake-cursor").css('top', top);
    $("#fake-cursor").css('left', left);
    if(force || top || left) $("#fake-cursor").attr("src","/static/images/hand.png").show();
}

function moveMouseTo(lookup, f) {
    var el = $(lookup).first();
    var top = el.first().offset()['top']+el.height()/2;
	var left = el.first().offset()['left']+el.width()/2;
	var lastClickedElement = null;
	$(document).setCookie('mouse-top', top);
	$(document).setCookie('mouse-left', left);
	$('#fake-cursor').animate({top:  top, left: left }, 1200, 'swing', function(){
	    if(lastClickedElement!=el) {
	        $("#fake-cursor").attr("src","/static/images/click.png");
            setTimeout(f, 500);
            setTimeout(function(){$("#fake-cursor").attr("src","/static/images/hand.png")}, 500);
        }
	    lastClickedElement = el;
	});
}

function recursively(element){
    if(element.length==0 && (cursor||document)!=document) {
        if (cursor.parentNode != null) cursor = cursor.parentNode; else cursor = document;
        return true
    }
    return false
}

function isIntoView(elem)
{
    var docViewTop = $(window).scrollTop();
    var docViewBottom = docViewTop + $(window).height();

    var elemTop = elem.offset().top;
    var elemBottom = elemTop + elem.height();

    return ((elemBottom <= docViewBottom-200) && (elemTop-52 >= docViewTop));
}

function scroolToElement(element, callback){
    var lastScrooledElement = null;
    if(element.offset() && !isIntoView(element)) {
        var scrollData = { scrollTop: element.offset().top - $(window).height()/2 };
        if(window['DISPLAY_FAKE_MOUSE']) var scroolSpeed = 1200;
        else var scroolSpeed = 0;
        // $([document.documentElement, document.body]).animate(scrollData, scroolSpeed, 'swing', function (){
        if($('#modal:visible').length>0){
            var container = '#modal';
            var scrollData = { scrollTop: element.offset().top - (window.innerHeight*0.25) + $(container).scrollTop()};
        } else {
            var container = 'body';
            var scrollData = { scrollTop: element.offset().top - (window.innerHeight*0.25)};
        }
        $(container).animate(scrollData, scroolSpeed, 'swing', function (){
            if(lastScrooledElement!=element) callback();
            lastScrooledElement = element;
        });
    } else {
        callback();
    }
    return element
}

function typeReturn(element){
    element.trigger({type: 'keypress', which: 13, keyCode: 13});
}

function typeTab(element){
    element.trigger({type: 'keypress', which: 9, keyCode: 9});
}

function click(name, type, index){

    if(index==null) index = 0;

    var element = [];
    var link = type==null || type=='link';
    var button = type==null || type=='button';
    var tab = type == 'tab';
    var icon = type == 'icon';
    if(icon){
        element = $(cursor||document).find('.bi-'+name+':visible').parent();
    }
    else if(tab){
        element = $(cursor||document).find('a.nav-link').filter(function() {return $(this).find('.nav-link-text').text().trim() == name;}).first();
    } else {
        if (element.length == 0 && (link || button)) element = $(cursor||document).find("button:visible").filter(function() {return $(this).text().replace('Loading...', '').trim() === name;}).first();
        if (element.length == 0 && (link || button)) element = $(cursor||document).find("a:visible").filter(function() {return $(this).text().replace('Loading...', '').trim() === name;}).first();
        if (element.length == 0 && (link || button)) element = $(cursor||document).find("a[name='" + name + "']").first();
    }

    if(recursively(element)){
        return click(name, type);
    } else if(element.length>0){
        if (window['DISPLAY_FAKE_MOUSE']) {
            showFakeMouse(true);
            function afterScrool() {
                function afterMoveMouse(){
                    $(element[index]).trigger('mouseover');
                    element[index].click();
                }
                moveMouseTo(element[index], afterMoveMouse);
            }
            return scroolToElement(element, afterScrool);
        } else {
            function afterScrool() {
                $("#fake-cursor").hide();
                $(element[index]).trigger('mouseover');
                element[index].click();
            }
            return scroolToElement(element, afterScrool);
        }
    }
    throw Error('Not found.')
}

function searchMenu(name){
    enter('search', name)
    return clickLink(name);
}

function clickLink(name){
    return click(name, 'link');
}

function clickTab(name){
    return click(name, 'tab');
}

function clickButton(name){
    return click(name, 'button');
}

function clickIcon(name, index){
    return click(name, 'icon');
}

function lookAtPopupWindow(){
    cursor = $('#modal')[0]
    return cursor;
}

function lookAt(text, only_panel){
    if(only_panel==true){
        var element = $(cursor||document).find(".panel-heading:visible").filter(function() {return $(this).text().trim() === text;}).first();
        if (element.length == 0) element = $(cursor||document).find("h1:visible").filter(function() {return $(this).text().trim() === text;}).first();
        if (element.length == 0) element = $(cursor||document).find("h2:visible").filter(function() {return $(this).text().trim() === text;}).first();
        if (element.length == 0) element = $(cursor||document).find("h3:visible").filter(function() {return $(this).text().trim() === text;}).first();
        if (element.length == 0) element = $(cursor||document).find("h4:visible").filter(function() {return $(this).text().trim() === text;}).first();
        if (element.length == 0) element = $(cursor||document).find("h5:visible").filter(function() {return $(this).text().trim() === text;}).first();
    } else {
        var element = $(cursor||document).find("tr:visible").filter(function() {return $(this).text().trim() === text;});
        if (element.length == 0) element = $(cursor||document).find("p:visible").filter(function() {return $(this).text().trim() === text;}).first();
        if (element.length == 0) element = $(cursor||document).find("div:visible").filter(function() {return $(this).text().trim() === text;}).first();
        if (element.length == 0) element = $(cursor||document).find("label:visible").filter(function() {return $(this).text().trim() === text;}).first();
    }
    if(recursively(element)){
        lookAt(text, only_panel);
    } else if(element.length>0){
        cursor = element[0];
        return element[0];
    }
    throw Error('Not found.')
}

function lookAtPanel(text){
    return lookAt(text, true);
}

function enter(name, value, submit){
    if(String(value)!='null' && String(value)){
        var tokens = value.split('/');
        if(tokens.length==3 && value[2]=='/' && value[5]=='/') value = tokens[2]+'-'+tokens[1]+'-'+tokens[0];
        var element = $(cursor||document).find( "input[name='"+name+"'], textarea[name='"+name+"']" ).not("input[type='checkbox']").not("input[type='hidden']").first();
        if (!element[0]) element = $(cursor||document).find( "label").filter(function() {return $(this).text().trim().replace('*', '') === name;}).parent().find('input, textarea').not("input[type='checkbox']").first();
        $('input[name=hidden-upload-value]').remove();
        if(element.prop("type")=='file'){
            $('<input type="hidden" name="hidden-upload-value" value="'+element[0].id+'">').appendTo(document.body);
            return element;
        }

        if(recursively(element)){
            return enter(name, value, submit);
        } else if(element.length>0) {
            function afterScrool() {
                element.focus();
                if (window['DISPLAY_FAKE_MOUSE'] && name != 'search') {
                    fakeType(element, value, 0);
                } else {
                    element.val(value);
                    var daterangepicker = element.data('daterangepicker');
                    if(daterangepicker){
                        setTimeout(function(){daterangepicker.hide()}, 500);
                    }
                }
                element.focus();
                if (submit) typeReturn(element);
            }
            return scroolToElement(element, afterScrool);
        }
        throw Error('Not found.')
    }
}

function check(name, radio, look){
    if(look==null) lookAt(name);
    if (radio) tipo = 'radio';
    else tipo = 'checkbox';
    var element = $(cursor||document).find('input[type='+tipo+']');
    if(recursively(element)){
        return check(name, radio, false);
    } else if(element.length>0){
        element.trigger('click');
        return element;
    }
    throw Error('Not found.')
}

function checkRadio(name){
    return check(name, true)
}

function validateChooseVal(name, value){
    var element = $(cursor||document).find( "select[name='"+name+"']" );
    if (!element[0]) element = $(cursor||document).find( "label:contains('"+name+"')" ).parent().find('select');
    if(recursively(element)){
        return choose(name, value, headless);
    } else {
        if(element.find("option:contains(" + value + ")").length>0){
            return true
        }
    }
    throw Error('Not found.')
}

function choose(name, value, headless){
    if(!value) return;

    var element = $(cursor||document).find( "select[name='"+name+"']" );
    if (!element[0]) element = $(cursor||document).find("label").filter(function() {return $(this).text().trim().replace('*', '') === name;}).parent().find('select');

    if(recursively(element)){
        return choose(name, value, headless);
    } else if(element.length>0) {
        if(headless){
            $(element).val(element.find("option:contains(" + value + ")").val());
        } else {
            function afterScrool() {
                element.select2("open");
                var $search = element.data('select2').dropdown.$search || element.data('select2').selection.$search;
                $search.val(value);
                $search.trigger('keyup');
                var lookup = "option:contains(" + value + ")";
                function waitValue() {
                    var value = element.find(lookup).val();
                    element.val(value).trigger('change');
                    element.select2('close');
                }
                setTimeout(waitValue, '2000');
            }
            return scroolToElement(element, afterScrool);
        }
        return element.parent()[0]
    }
    throw Error('Not found.')
}

function seeMessage(text){
    var message = $('.toast').first();
    if(message.text().trim().indexOf(text)>=0){
        message.click();
        return message;
    } else {
        throw Error('Message not found.')
    }
}

function wait(ms){
    var start = new Date().getTime();
    var end = start;
    while(end < start + ms) {
      end = new Date().getTime();
   }
 }

$(document).ready(function() {
    if(DISPLAY_FAKE_MOUSE) showFakeMouse();
});