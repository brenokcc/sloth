# Perguntas Frequentes

## Ações

**- Como defino os campos do formulário de cadastro para um determinado modelo**?

RESPOSTA: Defina o atributo "fieldsets" na classe Meta do modelo.

```
    class Meta:
        fieldsets = {'Dados Gerais': ('usuario', 'descricao', 'data_hora')}
```

**- Como sobrescrevo o formulário de cadastro padrão para um determinado modelo**?

RESPOSTA: Implemente uma ação iniciando com a palavra "Cadastrar".
Ex: CadastrarPessoa para o modelo Pessoa.

**- Como sobrescrevo o formulário de edição padrão para um determinado modelo**?

RESPOSTA: Implemente uma ação iniciando com a palavra "Editar".

Ex: EditarPessoa para o modelo Pessoa.

**- Como exibo informações de um objeto em um ação**?

RESPOSTA: Implemente o método display() da ação baseado no exemplo abaixo.

```
    def display(self):

       return self.instance.values('nome', ('estado', 'codigo'))
```

**- Como populo dinamicamente um select em um ação baseado no valor de outro campo**?

RESPOSTA: Implemente o método get_{field_name}_queryset() baseado no exemplo abaixo.

```
    estado = actions.ModelChoiceField(Estado.objects, label='Estado')
    cidade = actions.ModelChoiceField(Municipio.objects, label='Cidade')
    ...
    def get_cidade_queryset(self, queryset):
        return queryset.filter(estado=self.data['estado'])
```

## Papéis

**- O que são papéis**?

RESPOSTA: Papéis correspondem a grupos nos quais um usuário pode ser associado para habilitá-lo a
realizar um cojunto de funcionalidades no sistema. Um papel pode possuir múltiplos escopos, os quais
são utilizados para retringir o acesso a objetos de outros modelos.

**- Dê exemplo de papéis e possíveis escopos aos quais eles podem estar associado**?

RESPOSTA: "Gerente de Loja", o qual pode estar associado a "loja" onde ele trabalha, ou a "rede" a qual
a loja pertence. Outro exemple é "Funcionário", o qual pode estar associado ao seu "setor" de lotação,
ao "departamento" onde o setor está localizado, a "empresa" a qual ele percente, etc.

**- Como defino um papel relacionado a uma classe de modelo**?

RESPOSTA: Utilize o decorator @role() baseado no exemplo a seguir:

```
from sloth.db import models, role

@role('Gerente de Loja', username='cpf', loja='loja', rede='loja__rede')
class GerenteLoja:
    cpf = models.BrCpfField('CPF')
    loja = models.ForeignKey(Loja)
    ...
```

O primeiro parâmetro do decorator é o nome do perfil. O segundo (username) é usado para
definir qual atributo do modelo deve ser usado para criar o usuário caso ele não exista.
Os demais parâmetros são escopos, que poderão ser utilizados para retringir o acesso a
objetos de outros modelos.


**- ...**?


