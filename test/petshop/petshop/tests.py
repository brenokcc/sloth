from sloth.test import SeleniumTestCase


class TesteIntegracao(SeleniumTestCase):
    def test(self):
        self.create_superuser('admin', '123')
        self.login('admin', '123')
        self.click_menu('Doenças')
        self.click_button('Cadastrar')
        breakpoint()
        self.enter('Descrição', 'Raiva')
        self.check('Contagiosa')
        self.click_button('Cadastrar')
        self.see_message('Ação realizada com sucesso')
        self.see('Raiva')
        self.click_menu('Tipos de Procedimento')
        self.click_button('Cadastrar')
        self.enter('Descrição', 'Banho')
        self.enter('Valor', '65,00')
        self.click_button('Cadastrar')
        self.see_message('Ação realizada com sucesso')
        self.see('Banho')
        self.logout()
