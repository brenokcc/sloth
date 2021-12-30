from django.core.management import BaseCommand
from ...models import Instituicao, Gestor, Campus


class Command(BaseCommand):
    def handle(self, *args, **options):
        instituicoes = {}
        for linha in INSTITUICOES.split('\n'):
            nome, sigla, email = linha.split(';')
            instituicao = Instituicao.objects.filter(sigla=sigla).first() or Instituicao(sigla=sigla)
            instituicao.nome = nome
            instituicao.save()
            instituicoes[sigla] = instituicao
            gestor = Gestor.objects.filter(email=email).first() or Gestor(email=email)
            gestor.nome = 'Gestor'
            gestor.instituicao = instituicao
            gestor.save()
            Campus.objects.get_or_create(instituicao=instituicao, nome='Reitoria')
        for linha in CAMPI.split('\n'):
            instituicao, nome = linha.split(';')
            instituicao = instituicao.upper()
            Campus.objects.get_or_create(instituicao=instituicoes[instituicao], nome=nome)


INSTITUICOES = '''INSTITUTO FEDERAL DO ACRE;IFAC;reitoria@ifac.edu.br
INSTITUTO FEDERAL DO AMAPÁ;IFAP;reitoria@ifap.edu.br
INSTITUTO FEDERAL DO AMAZONAS;IFAM;gabinete@ifam.edu.br
INSTITUTO FEDERAL DO PARÁ;IFPA;gabinete.reitoria@ifpa.edu.br
INSTITUTO FEDERAL DE RONDÔNIA;IFRO;reitoria@ifro.edu.br
INSTITUTO FEDERAL DE RORAIMA;IFRR;gabinete.reitoria@ifrr.edu.br
INSTITUTO FEDERAL DE TOCANTINS;IFTO;reitoria@ifto.edu.br
NSTITUTO FEDERAL DE ALAGOAS;IFAL;secgab@ifal.edu.br
INSTITUTO FEDERAL BAIANO;IF BAIANO;gabinete@ifbaiano.edu.br
INSTITUTO FEDERAL DA BAHIA;IFBA;gabinete@ifba.edu.br
INSTITUTO FEDERAL DO CEARÁ;IFCE;reitoria@ifce.edu.br
INSTITUTO FEDERAL DO MARANHÃO;IFMA;gabinete@ifma.edu.br
INSTITUTO FEDERAL DA PARAÍBA;IFPB;gabinete.reitoria@ifpb.edu.br
INSTITUTO FEDERAL DE PERNAMBUCO;IFPE;gabinete@reitoria.ifpe.edu.br
INSTITUTO FEDERAL DO SERTÃO PERNAMBUCANO;IF SERTÃO-PE;reitoria@ifsertao-pe.edu.br
INSTITUTO FEDERAL DO PIAUÍ;IFPI;reitoria@ifpi.edu.br
INSTITUTO FEDERAL DO RIO GRANDE DO NORTE;IFRN;gabinete.reitoria@ifrn.edu.br
INSTITUTO FEDERAL DE SERGIPE;IFS;reitoria@ifs.edu.br
INSTITUTO FEDERAL DE BRASÍLIA;IFB;reitoria@ifb.edu.br
INSTITUTO FEDERAL GOIANO;IF GOIANO;gabinete@ifgoiano.edu.br
INSTITUTO FEDERAL DE GOIÁS;IFG;gabinete.reitoria@ifg.edu.br
INSTITUTO FEDERAL DO MATO GROSSO;IFMT;gabinete@ifmt.edu.br
INSTITUTO FEDERAL DE MATO GROSSO DO SUL;IFMS;reitoria@ifms.edu.br
INSTITUTO FEDERAL DO ESPÍRITO SANTO;IFES;gabinete@ifes.edu.br
CENTRO FEDERAL DE EDUCAÇÃO TECNOLÓGICA DE MINAS GERAIS;CEFET-MG;gabinete@adm.cefetmg.br
INSTITUTO FEDERAL DE MINAS GERAIS;IFMG;gabinete@ifmg.edu.br
INSTITUTO FEDERAL DO NORTE DE MINAS GERAIS;IFNMG;gabinete@ifnmg.edu.br
INSTITUTO FEDERAL DO SUDESTE DE MINAS GERAIS;IF SUDESTE MG;gabinete@ifsudestemg.edu.br
INSTITUTO FEDERAL DO SUL DE MINAS GERAIS;IF SUL DE MINAS;reitoria@IF SUL DE MINAS.edu.br
INSTITUTO FEDERAL DO TRIÂNGULO MINEIRO;IFTM;gabinete.reitoria@iftm.edu.br
CENTRO FEDERAL DE EDUCAÇÃO TECNOLÓGICA CELSO SUCKOW DA FONSECA;CEFET-RJ;direg@cefet-rj.br
COLÉGIO PEDRO II;CPII;reitoriagab@cp2.g12.br
INSTITUTO FEDERAL FLUMINENSE;IFF;reitoria@iff.edu.br
INSTITUTO FEDERAL DO RIO DE JANEIRO;IFRJ;gr@ifrj.edu.br
INSTITUTO FEDERAL DE SÃO PAULO;IFSP;gab@ifsp.edu.br
INSTITUTO FEDERAL DO PARANÁ;IFPR;gabinete@ifpr.edu.br
INSTITUTO FEDERAL FARROUPILHA;IF FARROUPILHA;gabreitoria@iffarroupilha.edu.br
INSTITUTO FEDERAL DO RIO GRANDE DO SUL;IFRS;gabinete@ifrs.edu.br
INSTITUTO FEDERAL SUL-RIO-GRANDENSE;IFSUL;reitoria@ifsul.edu.br
INSTITUTO FEDERAL CATARINENSE;IFC;gabinete@ifc.edu.br
INSTITUTO FEDERAL DE SANTA CATARINA;IFSC;gabinete.reitoria@ifsc.edu.br'''


CAMPI = '''CEFET-MG;Uned Araxá
CEFET-MG;Uned Contagem
CEFET-MG;Uned Curvelo
CEFET-MG;Uned Divinópolis
CEFET-MG;Uned Leopoldina
CEFET-MG;Uned Nepomuceno
CEFET-MG;Uned Timóteo
CEFET-MG;Uned Varginha
CEFET-MG;Unidade Belo Horizonte
CEFET-RJ;Uned Angra dos Reis
CEFET-RJ;Uned Itaguaí
CEFET-RJ;Uned Maria da Graça
CEFET-RJ;Uned Nova Friburgo
CEFET-RJ;Uned Nova Iguaçu
CEFET-RJ;Uned Petrópolis
CEFET-RJ;Uned Valença
CEFET-RJ;Unidade Maracanã
CPII;Campus Centro
CPII;Campus Duque de Caxias CP
CPII;Campus Engenho Novo I
CPII;Campus Engenho Novo II
CPII;Campus Humaitá I
CPII;Campus Humaitá II
CPII;Campus Niterói
CPII;Campus Realengo I
CPII;Campus Realengo II
CPII;Campus São Cristovão I
CPII;Campus São Cristóvão II
CPII;Campus São Cristóvão III
CPII;Campus Tijuca I
CPII;Campus Tijuca II
IF Baiano;Campus Alagoinhas
IF Baiano;Campus Bom Jesus da Lapa
IF Baiano;Campus Catu
IF Baiano;Campus Governador Mangabeira
IF Baiano;Campus Guanambi
IF Baiano;Campus Itaberaba
IF Baiano;Campus Itapetinga
IF Baiano;Campus Santa Inês
IF Baiano;Campus Senhor do Bonfim
IF Baiano;Campus Serrinha
IF Baiano;Campus Teixeira de Freitas
IF Baiano;Campus Uruçuca
IF Baiano;Campus Valença
IF Baiano;Campus Xique-Xique
IF Farroupilha;Campus Alegrete
IF Farroupilha;Campus Avançado Uruguaiana
IF Farroupilha;Campus Frederico Westphalen
IF Farroupilha;Campus Jaguari
IF Farroupilha;Campus Júlio de Castilhos
IF Farroupilha;Campus Panambi
IF Farroupilha;Campus Santa Rosa
IF Farroupilha;Campus Santo Ângelo
IF Farroupilha;Campus Santo Augusto
IF Farroupilha;Campus São Borja
IF Farroupilha;Campus São Vicente do Sul
IF Goiano;Campus Avançado Catalão
IF Goiano;Campus Avançado Hidrolândia
IF Goiano;Campus Avançado Ipameri
IF Goiano;Campus Campos Belos
IF Goiano;Campus Ceres
IF Goiano;Campus Cristalina
IF Goiano;Campus Iporá
IF Goiano;Campus Morrinhos
IF Goiano;Campus Posse
IF Goiano;Campus Rio Verde
IF Goiano;Campus Trindade
IF Goiano;Campus Urutaí
IF Sertão-PE;Campus Floresta
IF Sertão-PE;Campus Ouricuri
IF Sertão-PE;Campus Petrolina
IF Sertão-PE;Campus Petrolina Zona Rural
IF Sertão-PE;Campus Salgueiro
IF Sertão-PE;Campus Santa Maria da Boa Vista
IF Sertão-PE;Campus Serra Talhada
IF Sudeste MG;Campus Avançado Bom Sucesso
IF Sudeste MG;Campus Avançado Cataguases
IF Sudeste MG;Campus Avançado Ubá
IF Sudeste MG;Campus Barbacena
IF Sudeste MG;Campus Juiz de Fora
IF Sudeste MG;Campus Manhuaçu
IF Sudeste MG;Campus Muriaé
IF Sudeste MG;Campus Rio Pomba
IF Sudeste MG;Campus Santos Dumont
IF Sudeste MG;Campus São João del Rei
IFAC;Campus Cruzeiro do Sul
IFAC;Campus Rio Branco
IFAC;Campus Rio Branco Baixada do Sol
IFAC;Campus Sena Madureira
IFAC;Campus Tarauacá
IFAC;Campus Xapuri
IFAL;Campus Arapiraca
IFAL;Campus Avançado Maceió Benedito Bentes
IFAL;Campus Batalha
IFAL;Campus Coruripe
IFAL;Campus Maceió
IFAL;Campus Maragogi
IFAL;Campus Marechal Deodoro
IFAL;Campus Murici
IFAL;Campus Palmeira dos Índios
IFAL;Campus Penedo
IFAL;Campus Piranhas
IFAL;Campus Rio Largo
IFAL;Campus Santana do Ipanema
IFAL;Campus São Miguel dos Campos
IFAL;Campus Satuba
IFAL;Campus Viçosa
IFAM;Campus Avançado Boca do Acre
IFAM;Campus Avançado Iranduba
IFAM;Campus Avançado Manacapuru
IFAM;Campus Coari
IFAM;Campus Eirunepé
IFAM;Campus Humaitá
IFAM;Campus Itacoatiara
IFAM;Campus Lábrea
IFAM;Campus Manaus Centro
IFAM;Campus Manaus Distrito Industrial
IFAM;Campus Manaus Zona Leste
IFAM;Campus Maués
IFAM;Campus Parintins
IFAM;Campus Presidente Figueiredo
IFAM;Campus São Gabriel da Cachoeira
IFAM;Campus Tabatinga
IFAM;Campus Tefé
IFAP;Campus Avançado Oiapoque
IFAP;Campus Laranjal do Jari
IFAP;Campus Macapá
IFAP;Campus Porto Grande
IFAP;Campus Santana
IFB;Campus Brasília
IFB;Campus Ceilândia
IFB;Campus Estrutural
IFB;Campus Gama
IFB;Campus Planaltina
IFB;Campus Recanto das Emas
IFB;Campus Riacho Fundo
IFB;Campus Samambaia
IFB;Campus São Sebastião
IFB;Campus Taguatinga
IFBA;Campus Avançado Ubaitaba
IFBA;Campus Barreiras
IFBA;Campus Brumado
IFBA;Campus Camaçari
IFBA;Campus Euclides da Cunha
IFBA;Campus Eunápolis
IFBA;Campus Feira de Santana
IFBA;Campus Ilhéus
IFBA;Campus Irecê
IFBA;Campus Jacobina
IFBA;Campus Jequié
IFBA;Campus Juazeiro
IFBA;Campus Lauro de Freitas
IFBA;Campus Paulo Afonso
IFBA;Campus Porto Seguro
IFBA;Campus Salvador
IFBA;Campus Santo Amaro
IFBA;Campus Santo Antônio de Jesus
IFBA;Campus Seabra
IFBA;Campus Simões Filho
IFBA;Campus Valença Tento
IFBA;Campus Vitória da Conquista
IFC;Campus Araquari
IFC;Campus Avançado Abelardo Luz
IFC;Campus Avançado Sombrio
IFC;Campus Blumenau
IFC;Campus Brusque
IFC;Campus Camboriú
IFC;Campus Concórdia
IFC;Campus Fraiburgo
IFC;Campus Ibirama
IFC;Campus Luzerna
IFC;Campus Rio do Sul
IFC;Campus Santa Rosa do Sul
IFC;Campus São Bento do Sul
IFC;Campus São Francisco do Sul
IFC;Campus Videira
IFCE;Campus Acaraú
IFCE;Campus Acopiara
IFCE;Campus Aracati
IFCE;Campus Avançado Guaramiranga
IFCE;Campus Avançado Jaguaruana
IFCE;Campus Avançado Mombaça
IFCE;Campus Baturité
IFCE;Campus Boa Viagem
IFCE;Campus Camocim
IFCE;Campus Canindé
IFCE;Campus Caucaia
IFCE;Campus Cedro
IFCE;Campus Crateús
IFCE;Campus Crato
IFCE;Campus Fortaleza
IFCE;Campus Horizonte
IFCE;Campus Iguatu
IFCE;Campus Itapipoca
IFCE;Campus Jaguaribe
IFCE;Campus Juazeiro do Norte
IFCE;Campus Limoeiro do Norte
IFCE;Campus Maracanaú
IFCE;Campus Maranguape
IFCE;Campus Morada Nova
IFCE;Campus Paracuru
IFCE;Campus Pecém
IFCE;Campus Quixadá
IFCE;Campus Sobral
IFCE;Campus Tabuleiro do Norte
IFCE;Campus Tauá
IFCE;Campus Tianguá
IFCE;Campus Ubajara
IFCE;Campus Umirim
IFES;Campus Alegre
IFES;Campus Aracruz
IFES;Campus Avançado Viana
IFES;Campus Barra de São Francisco
IFES;Campus Cachoeiro de Itapemirim
IFES;Campus Cariacica
IFES;Campus Centro Serrano
IFES;Campus Colatina
IFES;Campus Guarapari
IFES;Campus Ibatiba
IFES;Campus Itapina
IFES;Campus Linhares
IFES;Campus Montanha
IFES;Campus Nova Venécia
IFES;Campus Piúma
IFES;Campus Santa Teresa
IFES;Campus São Mateus
IFES;Campus Serra
IFES;Campus Venda Nova do Imigrante
IFES;Campus Vila Velha
IFES;Campus Vitória
IFF;Campus Avançado Cambuci
IFF;Campus Avançado Maricá
IFF;Campus Avançado São João da Barra
IFF;Campus Bom Jesus do Itabapoana
IFF;Campus Cabo Frio
IFF;Campus Campos Centro
IFF;Campus Campos Guarus
IFF;Campus Itaboraí
IFF;Campus Itaperuna
IFF;Campus Macaé
IFF;Campus Quissamã
IFF;Campus Santo Antônio de Pádua
IFG;Campus Águas Lindas de Goiás
IFG;Campus Anápolis
IFG;Campus Aparecida de Goiânia
IFG;Campus Cidade de Goiás
IFG;Campus Formosa
IFG;Campus Goiânia
IFG;Campus Goiânia Oeste
IFG;Campus Inhumas
IFG;Campus Itumbiara
IFG;Campus Jataí
IFG;Campus Luziânia
IFG;Campus Senador Canedo
IFG;Campus Uruaçu
IFG;Campus Valparaíso de Goiás
IFMA;Campus Açailândia
IFMA;Campus Alcântara
IFMA;Campus Araioses
IFMA;Campus Avançado Carolina
IFMA;Campus Avançado Porto Franco
IFMA;Campus Avançado Rosário
IFMA;Campus Bacabal
IFMA;Campus Barra do Corda
IFMA;Campus Barreirinhas
IFMA;Campus Buriticupu
IFMA;Campus Caxias
IFMA;Campus Codó
IFMA;Campus Coelho Neto
IFMA;Campus Grajaú
IFMA;Campus Imperatriz
IFMA;Campus Itapecuru Mirim
IFMA;Campus Pedreiras
IFMA;Campus Pinheiro
IFMA;Campus Presidente Dutra
IFMA;Campus Santa Inês
IFMA;Campus São João dos Patos
IFMA;Campus São José de Ribamar
IFMA;Campus São Luís Centro Histórico
IFMA;Campus São Luís Maracanã
IFMA;Campus São Luís Monte Castelo
IFMA;Campus São Raimundo das Mangabeiras
IFMA;Campus Timon
IFMA;Campus Viana
IFMA;Campus Zé Doca
IFMG;Campus Avançado Arcos
IFMG;Campus Avançado Conselheiro Lafaiete
IFMG;Campus Avançado Ipatinga
IFMG;Campus Avançado Itabirito
IFMG;Campus Avançado Piumhi
IFMG;Campus Avançado Ponte Nova
IFMG;Campus Bambuí
IFMG;Campus Betim
IFMG;Campus Congonhas
IFMG;Campus Formiga
IFMG;Campus Governador Valadares
IFMG;Campus Ibirité
IFMG;Campus Ouro Branco
IFMG;Campus Ouro Preto
IFMG;Campus Ribeirão das Neves
IFMG;Campus Sabará
IFMG;Campus Santa Luzia
IFMG;Campus São João Evangelista
IFMS;Campus Aquidauana
IFMS;Campus Campo Grande
IFMS;Campus Corumbá
IFMS;Campus Coxim
IFMS;Campus Dourados
IFMS;Campus Jardim
IFMS;Campus Naviraí
IFMS;Campus Nova Andradina
IFMS;Campus Ponta Porã
IFMS;Campus Três Lagoas
IFMT;Campus Alta Floresta
IFMT;Campus Avançado Diamantino
IFMT;Campus Avançado Guarantã do Norte
IFMT;Campus Avançado Lucas do Rio Verde
IFMT;Campus Avançado Sinop
IFMT;Campus Avançado Tangará da Serra
IFMT;Campus Barra do Garças
IFMT;Campus Cáceres
IFMT;Campus Campo Novo do Parecis
IFMT;Campus Confresa
IFMT;Campus Cuiabá
IFMT;Campus Cuiabá Bela Vista
IFMT;Campus Juína
IFMT;Campus Pontes e Lacerda
IFMT;Campus Primavera do Leste
IFMT;Campus Rondonópolis
IFMT;Campus São Vicente
IFMT;Campus Sorriso
IFMT;Campus Várzea Grande
IFNMG;Campus Almenara
IFNMG;Campus Araçuaí
IFNMG;Campus Arinos
IFNMG;Campus Avançado Janaúba
IFNMG;Campus Avançado Porteirinha
IFNMG;Campus Diamantina
IFNMG;Campus Januária
IFNMG;Campus Montes Claros
IFNMG;Campus Pirapora
IFNMG;Campus Salinas
IFNMG;Campus Teófilo Otoni
IFPA;Campus Abaetetuba
IFPA;Campus Altamira
IFPA;Campus Ananindeua
IFPA;Campus Avançado Vigia
IFPA;Campus Belém
IFPA;Campus Bragança
IFPA;Campus Breves
IFPA;Campus Cametá
IFPA;Campus Castanhal
IFPA;Campus Conceição do Araguaia
IFPA;Campus Itaituba
IFPA;Campus Marabá Industrial
IFPA;Campus Marabá Rural
IFPA;Campus Óbidos
IFPA;Campus Paragominas
IFPA;Campus Parauapebas
IFPA;Campus Santarém
IFPA;Campus Tucuruí
IFPB;Campus Avançado Areia
IFPB;Campus Avançado Cabedelo Centro
IFPB;Campus Avançado João Pessoa Mangabeira
IFPB;Campus Avançado Pedras de Fogo
IFPB;Campus Avançado Soledade
IFPB;Campus Cabedelo
IFPB;Campus Cajazeiras
IFPB;Campus Campina Grande
IFPB;Campus Catolé do Rocha
IFPB;Campus Esperança
IFPB;Campus Guarabira
IFPB;Campus Itabaiana
IFPB;Campus Itaporanga
IFPB;Campus João Pessoa
IFPB;Campus Monteiro
IFPB;Campus Patos
IFPB;Campus Picuí
IFPB;Campus Princesa Isabel
IFPB;Campus Santa Luzia
IFPB;Campus Santa Rita
IFPB;Campus Sousa
IFPE;Campus Abreu e Lima
IFPE;Campus Afogados da Ingazeira
IFPE;Campus Barreiros
IFPE;Campus Belo Jardim
IFPE;Campus Cabo de Santo Agostinho
IFPE;Campus Caruaru
IFPE;Campus Garanhuns
IFPE;Campus Igarassu
IFPE;Campus Ipojuca
IFPE;Campus Jaboatão dos Guararapes
IFPE;Campus Olinda
IFPE;Campus Palmares
IFPE;Campus Paulista
IFPE;Campus Pesqueira
IFPE;Campus Recife
IFPE;Campus Vitória de Santo Antão
IFPI;Campus Angical do Piauí
IFPI;Campus Avançado José de Freitas
IFPI;Campus Avançado PIO IX
IFPI;Campus Avançado Teresina Dirceu Arcoverde
IFPI;Campus Campo Maior
IFPI;Campus Cocal
IFPI;Campus Corrente
IFPI;Campus Floriano
IFPI;Campus Oeiras
IFPI;Campus Parnaíba
IFPI;Campus Paulistana
IFPI;Campus Pedro II
IFPI;Campus Picos
IFPI;Campus Piripiri
IFPI;Campus São João do Piauí
IFPI;Campus São Raimundo Nonato
IFPI;Campus Teresina Central
IFPI;Campus Teresina Zona Sul
IFPI;Campus Uruçuí
IFPI;Campus Valença do Piauí
IFPR;Campus Assis Chateaubriand
IFPR;Campus Avançado Arapongas
IFPR;Campus Avançado Astorga
IFPR;Campus Avançado Barracão
IFPR;Campus Avançado Coronel Vivida
IFPR;Campus Avançado Goioerê
IFPR;Campus Avançado Quedas do Iguaçu
IFPR;Campus Campo Largo
IFPR;Campus Capanema
IFPR;Campus Cascavel
IFPR;Campus Colombo
IFPR;Campus Curitiba
IFPR;Campus Foz do Iguaçu
IFPR;Campus Irati
IFPR;Campus Ivaiporã
IFPR;Campus Jacarezinho
IFPR;Campus Jaguariaíva
IFPR;Campus Londrina
IFPR;Campus Palmas
IFPR;Campus Paranaguá
IFPR;Campus Paranavaí
IFPR;Campus Pinhais
IFPR;Campus Pitanga
IFPR;Campus Telêmaco Borba
IFPR;Campus Umuarama
IFPR;Campus União da Vitória
IFRJ;Campus Arraial do Cabo
IFRJ;Campus Avançado Mesquita
IFRJ;Campus Avançado Resende
IFRJ;Campus Belford Roxo
IFRJ;Campus Duque de Caxias
IFRJ;Campus Engenheiro Paulo de Frontin
IFRJ;Campus Nilópolis
IFRJ;Campus Niterói
IFRJ;Campus Paracambi
IFRJ;Campus Pinheiral
IFRJ;Campus Realengo
IFRJ;Campus Rio de Janeiro
IFRJ;Campus São Gonçalo
IFRJ;Campus São João de Meriti
IFRJ;Campus Volta Redonda
IFRN;Campus Apodi
IFRN;Campus Avançado Jucurutu
IFRN;Campus Avançado Lajes
IFRN;Campus Avançado Natal Zona Leste
IFRN;Campus Avançado Parelhas
IFRN;Campus Caicó
IFRN;Campus Canguaretama
IFRN;Campus Ceará-Mirim
IFRN;Campus Currais Novos
IFRN;Campus Ipanguaçu
IFRN;Campus João Câmara
IFRN;Campus Macau
IFRN;Campus Mossoró
IFRN;Campus Natal Central
IFRN;Campus Natal Cidade Alta
IFRN;Campus Natal Zona Norte
IFRN;Campus Nova Cruz
IFRN;Campus Parnamirim
IFRN;Campus Pau dos Ferros
IFRN;Campus Santa Cruz
IFRN;Campus São Gonçalo do Amarante
IFRN;Campus São Paulo do Potengi
IFRO;Campus Ariquemes
IFRO;Campus Avançado São Miguel do Guaporé
IFRO;Campus Cacoal
IFRO;Campus Colorado do Oeste
IFRO;Campus Guajará-Mirim
IFRO;Campus Jaru
IFRO;Campus Ji-Paraná
IFRO;Campus Porto Velho Calama
IFRO;Campus Porto Velho Zona Norte
IFRO;Campus Vilhena
IFRR;Campus Amajari
IFRR;Campus Avançado Bonfim
IFRR;Campus Boa Vista
IFRR;Campus Boa Vista Zona Oeste
IFRR;Campus Novo Paraíso
IFRS;Campus Alvorada
IFRS;Campus Avançado Veranópolis
IFRS;Campus Bento Gonçalves
IFRS;Campus Canoas
IFRS;Campus Caxias do Sul
IFRS;Campus Erechim
IFRS;Campus Farroupilha
IFRS;Campus Feliz
IFRS;Campus Ibirubá
IFRS;Campus Osório
IFRS;Campus Porto Alegre
IFRS;Campus Porto Alegre Restinga
IFRS;Campus Rio Grande
IFRS;Campus Rolante
IFRS;Campus Sertão
IFRS;Campus Vacaria
IFRS;Campus Viamão
IFS;Campus Aracaju
IFS;Campus Estância
IFS;Campus Itabaiana
IFS;Campus Lagarto
IFS;Campus Nossa Senhora da Glória
IFS;Campus Nossa Senhora do Socorro
IFS;Campus Poço Redondo
IFS;Campus Propriá
IFS;Campus São Cristóvão
IFS;Campus Tobias Barreto
IFSC;Campus Araranguá
IFSC;Campus Avançado São Lourenço do Oeste
IFSC;Campus Caçador
IFSC;Campus Canoinhas
IFSC;Campus Chapecó
IFSC;Campus Criciúma
IFSC;Campus Florianópolis
IFSC;Campus Florianópolis Continente
IFSC;Campus Garopaba
IFSC;Campus Gaspar
IFSC;Campus Itajaí
IFSC;Campus Jaraguá do Sul
IFSC;Campus Jaraguá do Sul Rau
IFSC;Campus Joinville
IFSC;Campus Lages
IFSC;Campus Palhoça
IFSC;Campus São Carlos
IFSC;Campus São José
IFSC;Campus São Miguel do Oeste
IFSC;Campus Tubarão
IFSC;Campus Urupema
IFSC;Campus Xanxerê
IFSP;Campus Araraquara
IFSP;Campus Avançado Ilha Solteira
IFSP;Campus Avançado Jundiaí
IFSP;Campus Avançado São Paulo - São Miguel
IFSP;Campus Avançado Tupã
IFSP;Campus Avaré
IFSP;Campus Barretos
IFSP;Campus Birigui
IFSP;Campus Boituva
IFSP;Campus Bragança Paulista
IFSP;Campus Campinas
IFSP;Campus Campos do Jordão
IFSP;Campus Capivari
IFSP;Campus Caraguatatuba
IFSP;Campus Catanduva
IFSP;Campus Cubatão
IFSP;Campus Guarulhos
IFSP;Campus Hortolândia
IFSP;Campus Itapetininga
IFSP;Campus Itaquaquecetuba
IFSP;Campus Jacareí
IFSP;Campus Matão
IFSP;Campus Piracicaba
IFSP;Campus Presidente Epitácio
IFSP;Campus Registro
IFSP;Campus Salto
IFSP;Campus São Carlos
IFSP;Campus São João da Boa Vista
IFSP;Campus São José do Rio Preto
IFSP;Campus São José dos Campos
IFSP;Campus São Paulo
IFSP;Campus São Paulo Pirituba
IFSP;Campus São Roque
IFSP;Campus Sertãozinho
IFSP;Campus Sorocaba
IFSP;Campus Suzano
IFSP;Campus Votuporanga
IFSUL;Campus Avançado Jaguarão
IFSUL;Campus Bagé
IFSUL;Campus Camaquã
IFSUL;Campus Charqueadas
IFSUL;Campus Gravataí
IFSUL;Campus Lajeado
IFSUL;Campus Novo Hamburgo
IFSUL;Campus Passo Fundo
IFSUL;Campus Pelotas
IFSUL;Campus Pelotas Visconde da Graça
IFSUL;Campus Santana do Livramento
IFSUL;Campus Sapiranga
IFSUL;Campus Sapucaia do Sul
IFSUL;Campus Venâncio Aires
IF SUL DE MINAS;Campus Avançado Carmo de Minas
IF SUL DE MINAS;Campus Avançado Três Corações
IF SUL DE MINAS;Campus Inconfidentes
IF SUL DE MINAS;Campus Machado
IF SUL DE MINAS;Campus Muzambinho
IF SUL DE MINAS;Campus Passos
IF SUL DE MINAS;Campus Poços de Caldas
IF SUL DE MINAS;Campus Pouso Alegre
IFTM;Campus Avançado Campina Verde
IFTM;Campus Avançado Uberaba Parque Tecnológico
IFTM;Campus Ituiutaba
IFTM;Campus Paracatu
IFTM;Campus Patos de Minas
IFTM;Campus Patrocínio
IFTM;Campus Uberaba
IFTM;Campus Uberlândia
IFTM;Campus Uberlândia Centro
IFTO;Campus Araguaína
IFTO;Campus Araguatins
IFTO;Campus Avançado Formoso do Araguaia
IFTO;Campus Avançado Lagoa da Confusão
IFTO;Campus Avançado Pedro Afonso
IFTO;Campus Colinas do Tocantins
IFTO;Campus Dianópolis
IFTO;Campus Gurupi
IFTO;Campus Palmas
IFTO;Campus Paraíso do Tocantins
IFTO;Campus Porto Nacional'''
