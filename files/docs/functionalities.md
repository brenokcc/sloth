# Functionalities

# Autenticação
- Autenticação padrão com login e senha
- Integração com provedores de autenticação Oauth2 como Facebook, Google, Github, etc.
- Habilitação de autenticação de dois fatores via aplicativo (qrcode) ou e-mail
- Recuperação de senha

# Tela de Login
- Exibição do nome da aplicação
- Exibição do logo da aplicação
- Exibição de um imagem ilustrativa
- Exibição de um texto explicativo
- Definição de uma máscara para o campo de login
- Exibição da versão da aplicação
- Inclusão de ações

## Ações

- Definir nome amigável, ícone, rótulo do botão
  - Meta-atributos verbose_name, icon e submit_label
- Estruturar a disposição dos campos
  - Meta-atributo fieldsets
- Exibir instruções para o usuário
  - Método get_instructions()
- Exibir informações associadas do objeto ao qual a ação se refere, quando aplicável
  - Método get_display()
- Redirecionar e exibir mensagem de sucesso
  - Métodod redirect()
- Exibir erros de validação
  - Métodos clean() e clean_{field_name}()
- Exibir dados após execução
  - Método render(template_name, data)
- Retornar dados no formato PDF
  - Método print(template_name, data)
- Retornar dados no formato XML
  - Método export(data)
- Retonar arquivo
  - Método download(file_path)
- Posibilitar a exibição e preenchimento dinâmicos de campos e fieldsets
  - Métodos on_{field_name}_change() show(), hide() e set()
- Possibilitar a população de seletores dinâmica baseada nos dados preenchidos pelo usuário
  - Método get_{field_name}_queryset()
- Controlar o acesso/permissão
  - Método has_permission(user)

## Visualização de Objetos (Model)

- Definição dos dados a serem exibidos
  - Método view() para retornar um ValueSet através do método values() 
- Agrupar informações para exibição
  - Métodos get_{fieldset_name}() para retornar um ValueSet através do método values() 
- Restringir acesso aos campos de um fieldset
  - Método has_get_{fieldset_name}_permission(user)
- Restringir acesso a um determinado campo
  - Métodos get_{fieldset_name}() e has_get_{fieldset_name}_permission(user)
- Ignorar campos baseado no papel do usuário
  - Método ignore(*field_names, role=None, roles=())
- Adicionar ações aos fieldsets
  - Método actions(*names) da classe ValueSet
- Definir um título customizado
  - Método title(name) da classe ValueSet
- Definir um subtítulo, a ser exibido abaixo no título
  - Método subtitle(name) da classe ValueSet
- Definir um status , a ser exibido abaixo do subtítulo/título
  - Método status(name) da classe ValueSet
- Anexar informações
  - Método attach(name) da classe ValueSet
- Adicionar informações
  - Método append(name) da classe ValueSet

## Listagem de Objetos (Manager)
- Definir os campos a serem exibidos
  - Método display(*names)
- Definir os campos de busca
  - Método search(*names)
- Definir os campos de pesquisa
  - Método filters(*names)
- Definir o limite da paginação
  - Método limit(total)
- Inibir campos e filtros
  - Método ignore(*names)
- Anexar informações para exibir no formato de abas
  - Método attach(*names)
- Adicionar informações para exibir simultaneamente
  - Método append(*names)
- Adicionar ações aos objetos
  - Método actions(*names)
- Adicionar ações ao cojunto
  - Método global_actions(*names)
- Adicionar ações em lote
  - Método batch_actions(*names)
- Definir subconjuntos
  - Método get_{fieldset_name}() para retornar um QuerySet através do método filter() 
- Gerar estatíticas sobre os objetos do conjunto
  - Métodos count(), sum() e avg()
- Restringir acesso as informações do conjunto
  - Método has_get_{fieldset_name}_permission(user)
- Permitir a visualização parcial dos objetos do conjunto
  - Método view(name)
- Definir a forma de exibição dos objetos como tabela, cartões, linhas, sanfona, linha do tempo, etc.
  - Métodos datatable(), cards(), rows(), accordion(), timeline(), etc
- Definir o template de exibição dos objetos
  - Método renderer(template_name)
- Exibir calendário para exibição de objetos com campo do tipo data e data/hora.
  - Método calendar(field_name)
