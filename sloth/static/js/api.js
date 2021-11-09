
function init(url, app, model, scope){
  // Begin Swagger UI call region
  const ui = SwaggerUIBundle({
    url: url,
    dom_id: '#swagger-ui',
    deepLinking: true,
    presets: [
      SwaggerUIBundle.presets.apis,
      SwaggerUIStandalonePreset
    ],
    plugins: [
      SwaggerUIBundle.plugins.DownloadUrl
    ],
    layout: "StandaloneLayout",
    onComplete: function (swaggerApi, swaggerUi) {
        loadSelects(app, model, scope);
    },
    persistAuthorization: true,
  });
  // End Swagger UI call region

  window.ui = ui;
}

window.onload = function() {
    init("/api/docs/");
}

function updateApi(clearModel){
    var app = document.getElementById('app').options[document.getElementById('app').selectedIndex].value;
    if(clearModel) document.getElementById('model').selectedIndex = 0;
    var model = document.getElementById('model').options[document.getElementById('model').selectedIndex].value;
    var scope = document.getElementById('scope').options[document.getElementById('scope').selectedIndex].value;
    var url = '/api/docs/?app='+app+'&model='+model+'&scope='+scope;
    init(url, app, model, scope);
}

function loadSelects(selectedApp, selectedModel, selectedScope){
    var request = new XMLHttpRequest();
    request.open('GET', '/api/docs/?filters=', false);
    request.onreadystatechange = handleStateChange;
    request.send(null);
    function handleStateChange() {
        if (request.readyState === 4) {
            if (this.status >= 200 && this.status < 300) {
                var data = JSON.parse(request.responseText);
                var apps = Object.keys(data['apps']);
                var scopes = Object.keys(data['scopes']);
                var appsOptions = '<option></option>';
                var modelsOptions = '<option></option>';
                var scopesOptions = '<option></option>';
                for(var i=0; i<apps.length; i++){
                    var selected = selectedApp == apps[i] ? 'selected' : '';
                    appsOptions+='<option '+selected+' value="'+apps[i]+'">'+apps[i]+'</option>';
                    if(!selectedApp || apps[i]==selectedApp){
                        for(var j=0; j<data['apps'][apps[i]].length; j++){
                            var model = data['apps'][apps[i]][j];
                            var selected = selectedModel == model[0] ? 'selected' : '';
                            modelsOptions+='<option '+selected+' value="'+model[0]+'">'+model[1]+'</option>';
                        }
                    }
                }
                for(var i=0; i<scopes.length; i++){
                    var selected = selectedScope == scopes[i] ? 'selected' : '';
                    scopesOptions+='<option '+selected+' value="'+scopes[i]+'">'+data['scopes'][scopes[i]]+'</option>';
                }
                var appsHtml = '<div><span class="servers-title">App</span><div class="servers"><label><select id="app" onchange="updateApi(true)" style="width:150px">'+appsOptions+'</select></label></div></div>';
                var modelsHtml = '<div><span class="servers-title">Models</span><div class="servers"><label><select id="model" onchange="updateApi()" style="width:150px">'+modelsOptions+'</select></label></div></div>';
                var scopesHtml = '<div><span class="servers-title">Scope</span><div class="servers"><label><select id="scope" onchange="updateApi()" style="width:150px">'+scopesOptions+'</select></label></div></div>';
                //var buttonHtml = '<button class="btn authorize"><span>Update</span></button>'
                document.getElementsByClassName('auth-wrapper')[0].insertAdjacentHTML('beforebegin', appsHtml+modelsHtml+scopesHtml);
            }
        }
    }
}