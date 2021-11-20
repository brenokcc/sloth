if($('.form-editar-pergunta, .form-adicionar-pergunta').length>0){
    $('#id_tipo_resposta').on('change', function(){
        if(this.value==8) $('.opcoes-de-resposta').show();
        else $('.opcoes-de-resposta').hide();
    });
    if($('#id_tipo_resposta').val()==8) $('.opcoes-de-resposta').show();
    else $('.opcoes-de-resposta').hide();
}
