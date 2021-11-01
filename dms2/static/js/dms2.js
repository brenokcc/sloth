$.datepicker.regional['pt-BR'] = {
    monthNames: ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'],
    monthNamesShort: ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'],
    dayNames: ['Domingo', 'Segunda', 'Terça', 'Quarta', 'Quita', 'Sexta', 'Sábado'],
    dayNamesShort: ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab'],
    dayNamesMin: ['Do', 'Se', 'Te', 'Qu', 'Qu', 'Se', 'Sa']
}
jQuery.expr[':'].icontains = function(a, i, m) {
  return jQuery(a).text().toUpperCase()
      .indexOf(m[3].toUpperCase()) >= 0;
};
jQuery.fn.extend({
    request: function(url, method, data, callback){
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
                        if(reader.result == '..'){
                            $(document).back()
                        } else if(reader.result && reader.result[0] == '/'){
                            $(document).open(reader.result);
                        } else {
                            callback(reader.result)
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
                    document.body.appendChild(a);
                    a.click();
                }
            },
            async: true,
            cache: false,
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
    popup: function(url, method, data){
        window['reloader'] = window['reload'+$(this).data('uuid')];
        $(this).request(url, method || 'GET', data || {}, function(html){
            $('#modal').find('.modal-body').html(html).initialize();
            $('#modal').modal('show');
        });
    },
    back: function(){
        if($('#modal').is(':visible')){
            $('#modal').modal('hide');
            if(window['reloader']) window['reloader']();
            else $(document).open(document.location.href);
        } else {
            if(window['reloader']) window['reloader']();
            else $(document).open(document.referrer);
        }
    },
    initialize: function (element) {
        $(this).find('.popup').on('click', function(e){
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
            if(method=='GET') var data = $(form).serialize();
            else var data = new FormData(form);
            $(document).request(form.action, method, data, function(html){
                if($('#modal').is(':visible')){
                    $('#modal').find('.modal-body').html(html).initialize();
                } else {
                    $('main').html(html).initialize();
                }
            });
            return false;
        });
        $(this).find('select').not('.select2-hidden-accessible').select2(
            {width: '100%', language: 'pt-BR', allowClear: true, placeholder: 'Selecione uma opção'}
        );
        $(this).find('.date-input').not('.hasDatepicker').datepicker(
            $.datepicker.regional['pt-BR']
        ).datepicker("option", "dateFormat", 'dd/mm/yy');
        $(this).find('.masked-input').each(function( index ) {
            $(this).mask($(this).data('mask'), {reverse: $(this).data('reverse')})
        });
    }
});
$( document ).ready(function() {
    $(document).initialize();
    document.cookie = "width="+$(window).width()+";path=/";
});
$( window ).resize(function() {
    console.log($(window).width());
    document.cookie = "width="+$(window).width()+";path=/";
});

