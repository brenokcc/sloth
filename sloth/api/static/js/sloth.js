jQuery.expr[':'].icontains = function(a, i, m) {
  return jQuery(a).text().toUpperCase()
      .indexOf(m[3].toUpperCase()) >= 0;
};
jQuery.fn.extend({
    request: function(url, method, data, callback, formcallback){
        var xhr = $.ajax({
            dataType:'binary',
            type: method,
            data: data,
            url:url,
            success: function(blob, status){
                var contentType = xhr.getResponseHeader("Content-Type");
                if(contentType.indexOf('text')>=0){
                    var reader = new FileReader();
                    reader.onload = function (event) {
                        if(reader.result.startsWith('<!---->') && reader.result.endsWith('<!---->')){
                            if(window['formcallback']){
                                result = reader.result.replace('$(document).back();', '$(document).back(true);');
                                setTimeout(function(){window['formcallback'](result);}, 500);
                            } else {
                                result = reader.result;
                            }
                            $(document.body).append(result);
                        } else {
                            callback(reader.result);
                        }
                    };
                    reader.readAsText(new Blob( [ new Uint8Array(blob ) ], { type: "text/html" } ));
                } else {
                    var file = window.URL.createObjectURL(new Blob( [ new Uint8Array(blob ) ], { type: contentType }));
                    var a = document.createElement("a");
                    a.href = file;
                    if (contentType.indexOf('excel') >= 0) a.download = 'Download.xls';
                    else if (contentType.indexOf('pdf') >= 0) a.download = 'Download.pdf';
                    else if (contentType.indexOf('zip') >= 0) a.download = 'Download.zip';
                    else if (contentType.indexOf('json') >= 0) a.download = 'Download.json';
                    else if (contentType.indexOf('csv') >= 0) a.download = 'Download.csv';
                    else if (contentType.indexOf('png') >= 0) a.download = 'Download.png';
                    document.body.appendChild(a);
                    a.click();
                    $(document).back(true);
                }
            },
            async: true,
            cache: true,
            contentType: false,
            processData: false,
            responseType:'arraybuffer'
        });
    },
    open: function(url, method, data){
        $(this).request(url, method || 'GET', data || {}, function(html){
            $('main').html(html).initialize();
        });
    },
    setUpPopupStack: function(){
        if(window['POPUP_STACK']==null){
            window['POPUP_STACK'] = [];
            window['POPUP_STACK_SELECT2'] = [];
            $('#modal').on('hidden.bs.modal', function (e) {
                if(window['POPUP_STACK'].length > 0){
                    $('#modal .modal-body').replaceWith(window['POPUP_STACK'].pop().initialize());
                    $('#modal').modal('show');
                    $('#modal').find('.modal-body').css('visibility', 'visible');
                    var vals = window['POPUP_STACK_SELECT2'].pop();
                    for(k in vals) {$('#'+k).val(vals[k]).trigger('change')}
                }
                else $('#modal').find('.modal-body').html('');
                testLoggerIdent = testLoggerIdent.substring(0, 8-4);
            });
            $('#modal').on('shown.bs.modal', function (e) {
                $('#modal').responsive();
                testLoggerIdent += '    ';
                testlogger("self.look_at_popup_window()");
                var h2 = $('#modal').find('h2');
                if(h2.length) testlogger("self.look_at('"+$(h2[0]).text().trim()+"')");
            });
        }
    },
    ipopup: function(url){
        var html = '<iframe src="'+url+'" width="100%" height="500px"></iframe>';
        $('#modal').setUpPopupStack();
        $('#modal').find('.modal-body').html(html);
        $('#modal').modal('show');
        $('#modal').find('.modal-body').css('visibility', 'visible');
    },
    popup: function(url, method, data){
        $('.alert-dismissible').hide();
        if(url.indexOf('?')>0) url = url+='&modal=1'
        else url+='?modal=1'
        $('#modal').setUpPopupStack();
        if($('#modal').find('.modal-body').html().trim()){
            $('#modal').find('.modal-body').css('visibility', 'hidden');
            $('#modal .modal-body .select2-hidden-accessible').select2("destroy");
            window['POPUP_STACK'].push($('#modal').find('.modal-body').clone());
            var vals={}; var elements=$('.modal-body select');
            for(var i=0; i<elements.length; i++) vals[elements[i].id] = $(elements[i]).val();
            window['POPUP_STACK_SELECT2'].push(vals);
        }
        $(this).request(url, method || 'GET', data || {}, function(html){
            $('#modal').find('.modal-body').html(html).initialize();
            if($('.modal-body input[type=text]:first').length > 0){
                window.setTimeout(function () {
                    //$('.modal-body').find('input[type=text], input[type=number]').first().focus();
                }, 200);
            }
            $('#modal').modal('show');
            $('#modal').find('.modal-body').css('visibility', 'visible');
        });
    },
    redirect: function(url){
        $('#modal').modal('hide');
        document.location.href = url;
    },
    download: function(url){
        alert(url);
        var a = document.createElement("a");
        a.href = url;
        document.body.appendChild(a);
        a.click();
        $(document).back();
    },
    back: function(canceled){
        if($('#modal').is(':visible')){
            $('#modal').modal('hide');
        } else {
            //$(document).open(document.referrer);
            //window.history.pushState("string", "Title", document.referrer);
            if(!canceled) document.location.href = document.referrer;
        }
        return this;
    },
    responsive: function(){
        $(this).find('.responsive-container > div').each(function (index) {
            var width = $(this).parent().width();
            if(width==0) width = $(window).width(); // popup
            $(this).removeClass('n').removeClass('s').removeClass('m').removeClass('l');
            if (width > 900) {
                $(this).addClass('l');
            } else if (width > 600) {
                $(this).addClass('m');
            } else if (width > 300) {
                $(this).addClass('s');
            } else {
                $(this).addClass('n');
            }
            //$(this).css('visibility', 'visible');
        });
        document.cookie = "width="+$(window).width()+";path=/";
        return this;
    },
    getCookie: function(name) {
      var match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
      if (match) return match[2];
    },
    setCookie: function(name, value) {
        document.cookie = name+"="+value+"; path=/";
    },
    initialize: function () {
        initTestLogger(this);
        $(this).find('a.popup').on('click', function(e){
            $(this).popup(this.href);
            e.preventDefault();
            return false;
        });
        $(this).find('.ajax').on('click', function(e){
            $(this).open(this.href);
            e.preventDefault();
            return false;
        });
        $(this).find('.form').on('submit', function(e){
            var form = this;
            var method = form.method.toUpperCase();
            if(method=='GET'){
                var data = $(form).serialize();
            } else {
                var data = new FormData(form);
                $(form).find('.image-input').each(function( index ) {
                    var blob = $(this).data('blob');
                    if(blob){
                        data.delete(this.name);
                        data.append(this.name, blob, new Date().getTime()+'.'+blob.type.split('/')[1]);
                    }
                });
            }
            $(document).request(form.action, method, data, function(html){
                $(form).closest('.action-wrapper').html($(html).find('.action-wrapper').html()).initialize();
                $(form).find('.btn-submit').removeClass('disabled').find('.spinner-border').addClass('d-none');
            });
            return false;
        });
        $(this).find('.field-controller').each(function( index ) {
            var widgets = $('.'+this.name);
            $(this).on('click', function(e){
                $(widgets).prop('disabled', !this.checked);
            });
            $(widgets).prop('disabled', !this.checked);
        });
        $(this).find('textarea.html-input').each(function( index ) {
            $(this).trumbowyg({lang: 'pt_br'});
        });
        $(this).find('select').not('.select2-hidden-accessible').each(function( index ) {
            var element = $(this);
            var url = $(this).data('choices-url');
            var ajax = {
                url: function(){ return url+'&'+$(this).closest('form').serialize(); },
                dataType: 'json', delay: 250, minimumInputLength: 3,
                data: function (params) {return { term: params.term };},
                processResults: function (data) {
                    data.items.forEach(function(data){
                        if(element.find("option[value='" + data.id + "']").length==0){
                            var option = new Option(data.text, data.id, false, false);
                            element.append(option);
                        }
                    });
                    return { results: data.items };
                },
                templateResult: function (data) {return data.html || 'Buscando...';},
                templateSelection: function (data) {return data.text;}
            }
            if(url==null) ajax = null;
            $(this).select2(
                {ajax: {delay: 3000}, width: '100%', language: 'pt-BR', allowClear: true, placeholder: '', ajax:ajax,
                templateResult: function(item){return item.html ? $(item.html) : item.text}}
            ).on("select2:open", function (e) { });
        });
        $(this).find('.masked-input').each(function( index ) {
            $(this).mask($(this).data('mask'), {reverse: $(this).data('reverse')})
        });
        $(this).responsive();
        $(this).find('[data-toggle="tooltip"]').tooltip();
        $(this).find('.image-input').each(function( index ) {
            var input = this;
            input.addEventListener('change', function (e) {
                if (e.target.files) {
                    let imageFile = e.target.files[0];
                    var reader = new FileReader();
                    reader.onload = function (e) {
                        const MAX_WIDTH = $(input).data('max-width') || 800;
                        var img = document.createElement("img");
                        img.id = input.id+'img';
                        img.onload = function (event) {
                            const ratio = MAX_WIDTH/img.width;
                            var canvas = document.createElement("canvas");
                            const ctx = canvas.getContext("2d");
                            canvas.height = canvas.width * (img.height / img.width);
                            const oc = document.createElement('canvas');
                            const octx = oc.getContext('2d');
                            oc.width = img.width * ratio;
                            oc.height = img.height * ratio;
                            octx.drawImage(img, 0, 0, oc.width, oc.height);
                            ctx.drawImage(oc, 0, 0, oc.width * ratio, oc.height * ratio, 0, 0, canvas.width, canvas.height);
                            oc.toBlob(function(blob){
                                $(input).addClass('resized-image');
                                $(input).data('blob', blob);
                            });
                            $('#cotainer'+img.id).remove();
                            $(img).css('max-width', '200px').css('margin', '20px');
                            var container = document.createElement("div");
                            container.id = 'cotainer'+img.id;
                            $(container).css('text-align', 'center').append(img);
                            $(input).parent().append(container);
                        }
                        img.src = e.target.result;
                    }
                    reader.readAsDataURL(imageFile);
                }
            });
        });
        $(document).on('select2:open', () => {
            $(this).closest('.select2-search__field').focus();
        });
        $('.fieldset-tab').map(function (i, item){var fieldsets=$(this).find('.reloadable-fieldset, .reloadable-queryset'); if(fieldsets.length == 1) fieldsets.find('.queryset-title, .fieldset-title').hide();});
        return this;
    },
    refresh: function(areas){
        function reloadAreas(){
            $('.reloadable-fieldset, .reloadable-queryset, .reloadable').map(
                function(i, item){
                    var querystring = '';
                    var qsform = $('#form-'+item.id);
                    if(qsform.length>0) querystring = '?'+qsform.serialize();
                    var url = $(item).data('path')+querystring;
                    if(areas && areas.length>0 && areas.indexOf(item.id)<0) return;
                    $.get(url, function(html){
                        if($(item).find('.bi-chevron-right').length){html=html.replace('bi-chevron-down', 'bi-chevron-right');}
                        $(item).html($(html).html()).initialize();
                    })
                    //console.log(item.id + ' : ' + url);
                    return {id: item.id, url: url}
                }
            ).get();
        } setTimeout(reloadAreas, 1000);
    },
    dynamic: function(name, initial){
        var form = $(this);
        var lastChangedValue = {};
        initial.hide.forEach(function(name) {
            form.find("input[name="+name+"], select[name="+name+"], textarea[name="+name+"]").closest('.form-field').hide();
        });
        initial.hide_fieldset.forEach(function(name) {
            form.find("."+name).hide();
        });
        $("input[name="+name+"],select[name="+name+"],textarea[name="+name+"]").change(
            function(){
                var value = $(this).val();
                if(value=='on') value = $(this).prop('checked');
                if(lastChangedValue[name]==value) return;
                else lastChangedValue[name]=value;
                var data = form.serialize();
                data += '&on_change_field='+name+'&on_change_value='+value;
                $.post(form.prop('action'), data, function(data){
                    data['hide_fieldset'].forEach(function(name) {
                        form.find('.'+name).hide();
                    });
                    data['show_fieldset'].forEach(function(name) {
                        form.find('.'+name).show();
                    });
                    data['hide'].forEach(function(field_name) {
                        form.find("input[name="+ field_name +"], select[name="+ field_name +"], textarea[name="+ field_name +"]").closest('.form-field').hide();
                    });
                    data['show'].forEach(function(field_name) {
                        form.find("input[name="+ field_name +"], select[name="+ field_name +"], textarea[name="+ field_name +"]").closest('.form-field').show();
                    });
                    data['set'].forEach(function(field) {
                        var widget = form.find("input[name=" + field.name + "],select[name=" + field.name + "],textarea[name=" + field.name + "]");
                        if(field.text){
                            if (false && widget.find("option[value=" + field.value + "]").length) widget.val(data.value).trigger('change');
                            else widget.append(new Option(field.text, field.value, true, true)).trigger('change');
                        } else {
                            widget.val(field.value);
                        }
                    });
                });
            }
        );
    }
});
$( document ).ready(function() {
    $(document).initialize();
    $('body').css('visibility', 'visible');
    $(document).setCookie('current_tab', '');
});
$( window ).resize(function() {
    $(document).responsive();
});