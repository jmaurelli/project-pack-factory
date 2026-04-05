export const sessionValidationUrl: string = '/afa/php/SuiteLoginSessionValidation.php';
export const SSOUrl: string = '/afa/php/SSOLogin.php';
export const bflowHealthUrl: string = '/BusinessFlow';
export const affHealthUrl: string = '/aff/api/internal/noauth/getStatus';
@Injectable({
    providedIn: 'root'
})

export class LoginService implements ILoginService {
    private headers: HttpHeaders;
    private httpParams: HttpParams;
    private httpOptions: Object;
    private search:any;
    private hash: string = '';
    private afaUrlRegex: RegExp = new RegExp('');
    private affUrlRegex: RegExp = new RegExp('');
    private appVizUrlRegex: RegExp = new RegExp('');
    private autoDiscovery: RegExp = new RegExp('');
    private swaggerRegex: RegExp = new RegExp('');
    public propertiesByProductMap:any = {
        'afa': {
            'loginRedirection': '/fa/server/connection/login',
            'userNameParam': 'username',
            'passwordParam': 'password',
            'forceLocalAuthParam': 'forceLocalAuth',
            'domainParam': 'domain'
        },
        'aff': {
            'loginRedirection': '/FireFlow/SelfService/CheckAuthentication/',
            'userNameParam': 'user',
            'passwordParam': 'pass',
            'forceLocalAuthParam': 'forceLocalAuth',
            'domainParam': 'domain'
        },
        'abf': {
            'loginRedirection': '/BusinessFlow/rest/v1/login',
        }
    };

	constructor(private http: HttpClient) {
        this.headers = new HttpHeaders().set('Content-Type', 'application/json');
        this.httpParams = new HttpParams();
        this.httpOptions = {
          params: this.httpParams,
          headers: new HttpHeaders({
            responseType: 'json',
            contentType: "application/json; application/x-www-form-urlencoded",
            Authorization:'my-auth-token'
          })
        };
        this.initUrlWhiteList();
      }

    async getSetup(){
        const response = await fetch("/seikan/login/setup");
        const body = await response.json();
        var affEnabled = body.isAffEnabled;
        var abfEnabled = body.isAbfEnabled;
        if (affEnabled){
            // aff health check
            const affResponse = await fetch(affHealthUrl);
            console.log('affResponse = ', affResponse);
            // If aff enabled, check bflow as well if needed.
            if(abfEnabled){
              // bflow health check
              const abfResponse = await fetch(bflowHealthUrl);
              console.log('abfResponse  = ', abfResponse);
            }
        } else if(abfEnabled){
             // bflow health check
             await fetch(bflowHealthUrl).then(() =>{console.log("bflow works properly");body});
        }
        return body;
    }

    validateSession(isDoClean: boolean):Promise<ISessionValidation> {
        let httpHeaders = new HttpHeaders().set('Content-Type', 'text/html;charset=UTF-8').set('Response-Type', 'text/html;charset=UTF-8');
        this.httpOptions={params: this.httpParams,headers: httpHeaders};
        return new Promise((resolve, reject) => {this.http.post(sessionValidationUrl + '?clean=' + isDoClean, this.httpOptions).subscribe(
            (response:any) => {
                console.log('HTTP response received Valition Session: ' , response);
                 resolve(typeof response === 'string' ? JSON.parse(response) : response);

            },
            (error:any)=>{
                console.log('HTTP ERROR received: ' + error);
                 reject(null)
            },
            () => console.log("HTTP request completed")
        )
        })

    }

    private static calcLoginSystem(suiteInfo: ISuiteInfo, loginSystemOverride: string) : string {
        if (loginSystemOverride) {
            return loginSystemOverride;
        } else if (suiteInfo.affEnabled && !suiteInfo.affVersionMismatch) {
            return "aff";
        } else if (suiteInfo.abfEnabled ) {
            return "abf";
        } else {
            return "afa";
        }
    }

    getHttpOptions(params:ILoginParams){

        var authdata = 'Basic ' + btoa(params.userName + ":" + params.password);
        var httpHeaders:HttpHeaders;
        httpHeaders = new HttpHeaders().set('Content-Type', 'application/json').set('Authorization', authdata);
        return this.httpOptions={headers:httpHeaders,params: this.httpParams,responseType: 'json', contentType: 'application/json; charset=utf-8'}
    }

    setBody(body:URLSearchParams,params: ILoginParams, loginSystem:string){
        body.set(this.propertiesByProductMap[loginSystem]["userNameParam"],params.userName);
        body.set(this.propertiesByProductMap[loginSystem]["passwordParam"],params.password);
        body.set('forceLocalAuth',params.forceLocalAuth)
        body.set('login','1')
    }

	submitLogin(suiteInfo: ISuiteInfo, params: ILoginParams, loginSystemOverride: string):Promise<any>{

        var loginSystem = LoginService.calcLoginSystem(suiteInfo, loginSystemOverride);
        var body= new URLSearchParams();
        if (loginSystem === 'abf') {
            this.httpOptions = this.getHttpOptions(params);
        } else if (loginSystem === 'afa') {
            this.setBody(body,params, loginSystem);
            this.httpOptions = {params: this.httpParams,headers: new HttpHeaders().set('Content-Type', 'application/x-www-form-urlencoded') ,responseType: 'application/json;charset=UTF-8'}
        }else{
            this.setBody(body,params, loginSystem);
            this.httpOptions = {params: this.httpParams,headers: new HttpHeaders().set('Content-Type', 'application/x-www-form-urlencoded') ,responseType: 'text/html; charset=utf-8'}

        }
         return new Promise((resolve, reject) => {'/'+this.http.post(this.propertiesByProductMap[loginSystem]['loginRedirection'], body.toString(),this.httpOptions).subscribe(
            (response:any) => {


                // In general:
                // in AFA returns the relevant HTTP error code, so in case of a failure it will get to the "catch" statement.
                // in case of successful login: will not find the "LoginErrorMessage" so will return with status OK.

                // TODO: investigate AFF login to avoid double login.

                // in AFF - CheckAuthentication always returns 200, so we need to look for the error message -
                // if an error message was found, we'll throw it
                // if not - successful login.
                if (loginSystem === "aff") {
                  var affLoginStatus: LoginStatus = this.handleFireFlowLoginResponse(response);
                    if (affLoginStatus.status != 200) {
                        if (suiteInfo.abfEnabled ) {
                            resolve (this.submitLogin(suiteInfo, params, "abf"));
                        } else {
                             resolve (this.submitLogin(suiteInfo, params, "afa"));
                        }
                    }else{
                        console.log('HTTP response received aff: ' + response);
                        resolve (200);
                    }
                }

                else if (loginSystem === "abf") {
                    // get AFA + AFF cookies
                    let httpHeaders = new HttpHeaders().set('Content-Type', 'text/html;charset=UTF-8').set('Response-Type', 'text/html;charset=UTF-8');
                    this.httpOptions={params: this.httpParams,headers: httpHeaders};
                         resolve(new Promise((resolve1, reject1) => {this.http.get("/BusinessFlow/login_ok",   {responseType: 'text'})
                        .subscribe(
                            (response:any) => {

                                console.log('HTTP response abf received');
                                resolve1 (200);
                            },
                            (error:any) => {
                                console.log('HTTP ERROR received abf: ' + error);
                                reject1 (500);
                        // we should get here only if the authentication succeeded (rest/v1/login). if for some reason login_ok failed at this stage - return internal error
                    })}))}
                else{
                    console.log('HTTP response received afa: ' + response);
                    resolve(200);
                }}
                ,
            (error:any) => {
                if (!error || !error.rejection || !error.rejection.status) {
                    reject (500); // return a general internal error code in case the error doesn't contain a status code
                }
                console.log('HTTP ERROR received: ' + error.rejection.status);
                  reject (error.rejection.status);
            }
            )})

    }

    handleFireFlowLoginResponse(response:any) {
        let isAuthenticated;
        if ( typeof response === "string" && response) {
            isAuthenticated = JSON.parse(response).authenticated;
		}

        if (response == null || typeof isAuthenticated === 'undefined') {
            return new LoginStatus("No authentication data in the response", 500);
        }
        if (isAuthenticated === 1) {
            return new LoginStatus("Login OK", 200);
        } else {
            var errorMessage = response.errorMessage;
            if (errorMessage == null) {
                return new LoginStatus("Internal problem", 500);
            }
            if (errorMessage.indexOf('password') >= 0) { // The full error message is 'Incorrect user name or password'
                return new LoginStatus(errorMessage, 401);
            } else {
                return new LoginStatus(errorMessage, 500);
            }
        }
    }

    submitFirstTimeAdmin(params: IFirstTimeParams) {
        this.headers = new HttpHeaders().set('Content-Type', 'application/x-www-form-urlencoded');
        this.httpParams = new HttpParams();
        this.httpOptions = {headers: this.headers, params: this.httpParams, responseType: 'text/html;charset=UTF-8'};
        let body = new URLSearchParams();
        body.set('username',params.username);
        body.set('fullname',params.fullname);
        body.set('email',params.email)
        body.set('password',params.password)

        return new Promise((resolve, reject) => {this.http.post('/afa/php/FirstTimeSetup.php', body.toString(), this.httpOptions).subscribe(
             (response:any) => {
                 console.log('HTTP response received: ', {response});
                  resolve(200);
             },
             (error:any)=> {
                 console.log('HTTP ERROR received: ', {error});
                 if (!error || (!error.status && (!error.rejection || !error.rejection.error))) {
                      reject(500); // return a general internal error code in case the error doesn't contain a status code
                 }
                 error = error.rejection;
                 if (error.status === 400) {
                      reject(error);
                 }
                 reject(error);
             },
             () => console.log("HTTP request completed")
        )
     })
 }

 initUrlWhiteList(){
    this.afaUrlRegex = this.generateAfaUrlRegex();
    this.affUrlRegex = this.generateFireFlowUrlRegex();
   this.appVizUrlRegex = this.generateAppVizUrlRegex();
   this.autoDiscovery = this.generateAutoDiscoveryUrlRegex();
   this.swaggerRegex = this.generateSwaggerUrlRegex();
 }

 generateSwaggerUrlRegex() {
    let spec = '\\?urls\\.primaryName=-*[A-Za-z_]+';
    let controller = '[\\w+-]+';
    let method = '/\\w+Using(?:GET|POST|PUT|DELETE)';
    let swaggerPath = '^/algosec/swagger/swagger-ui\\.html(?:' + spec + '(?:#/)?(?:' + controller + '(?:' + method + ')?)?)?$';
    return new RegExp(swaggerPath);
}

generateAutoDiscoveryUrlRegex(){
	  let autoDiscoveryPath = '^/AutoDiscovery/?(?:index\\.html)?$'
    return new RegExp(autoDiscoveryPath);
}

generateAfaUrlRegex() {
    function getSuitePathAsRegex() {

        let routeParamsRegex = '[A-Za-z0-9_-]+';
        let reportUrlSuffix = [
            'baseline-compliance',
            'optimize-policy',
            'optimize-policy/covered-rules',
            'optimize-policy/tighten-permissive-rules',
            'regulatory-compliance',
            'vpn',
            'policy',
            'risks',
            'home',
            'risky-rules',
            'changes',
            'changes/rules',
            'changes/policy',
            'changes/topology',
            'changes/risks',
            'changes/baseline-compliance',
            'changes/vpn',
            'changes/audit',
            'changes/configuration'
        ];

        const changesUrlsSuffix = [
          'changes/snapshot',
          'changes/interval'
        ];

        let suiteUrlSuffix = [
            'issues-center',
            'map-completeness',
            'query-result'
        ];
        let suitePrefix = '/algosec-ui/';
        let reportPathAsRegex = suitePrefix + 'report/' + routeParamsRegex + '(?:/' + UtilsService.asRegex(reportUrlSuffix) + ')?';
        let suitePathAsRegex = suitePrefix +  UtilsService.asRegex(suiteUrlSuffix);
        const changesPathsAsRegex = suitePrefix + UtilsService.asRegex(changesUrlsSuffix) + '/' + routeParamsRegex + '(?:/' + UtilsService.asRegex(CHANGES_TABS_URLS) + ')?';
        return UtilsService.asRegex(reportPathAsRegex, suitePathAsRegex, changesPathsAsRegex);
    }
    function getAfaPathAsRegex() {

        let afaSuffixPartialList = [
            'home',
            'status'
        ]
        let administrationSuffixList = [
            'users_management',
            'distribution_management',
            'integrations',
            'monitoring',
            'options',
            'scheduler',
            'compliance',
            'data_collection'
        ];
        let afaPathSuffixList = afaSuffixPartialList.concat(administrationSuffixList);
        return '/afa/php/' + UtilsService.asRegex(afaPathSuffixList) + '\\.php';
    }
    let afaPathRegex = getAfaPathAsRegex();
    let suitePathRegex:any = getSuitePathAsRegex();

    return new RegExp('^' + UtilsService.asRegex(afaPathRegex,suitePathRegex) + '$');
}

generateFireFlowUrlRegex() {
    let noHackingChars = '[^\"\'`]+';
    let fireFlowPaths = [
        'Ticket/Display\\.html\\?id=\\d+',
        'Ticket/Attachment/\\d+/\\d+/Ticket_\\d+_Work_Order\\.pdf',
        'Dashboards/\\d/' + noHackingChars,
        'Search/(?:ManageCharts|ByRule)\\.html',
        'Reconciliation/index\\.html',
        'Template/index\\.html',
        'Admin/(?:Users|Groups|CustomFields|Global/CLogic|SLANotifications|Advanced|Advanced/Configuration|Global)/index\\.html'
    ];
    let fireFlowUrlRegex = '/FireFlow/' +  UtilsService.asRegex(fireFlowPaths);
    let faUrlRegex = '/fa/query/results/#/work/' + noHackingChars + '/?' + '(?:' + noHackingChars + ')?';
    let affUrlRegex = '/aff/#/aff/ng/changeRequests/fromTemplate/\\d+';
    return new RegExp('^' + UtilsService.asRegex('/VisualFlow/', fireFlowUrlRegex, faUrlRegex, affUrlRegex) + '$');
}

generateAppVizUrlRegex() {
    function getAdministrationPathAsRegex() {
        function getSettingsPathAsRegex() {
            let customizationPathsList = [
                'fields',
                'labels/Application',
                'critical_processes',
                'cr/(?:application|object)'];

            let objectsUpdatePathsList = [
                '(?:afa|cmbd|file)/manage',
                '(?:afa|file)/report/endpoints'];

            let settingsPathsPartialList = [
                'import',
                'discovery',
                'va',
                'activities',
                'user/email'];

            let settingsPathsPartialRegex = UtilsService.asRegex(settingsPathsPartialList);
            let customizationPathRegex = 'customization/?(?:/' + UtilsService.asRegex(customizationPathsList) + ')?';
            let objectsUpdatePathRegex = 'objects_update/?(?:/' + UtilsService.asRegex(objectsUpdatePathsList) + ')?';
            return 'settings/' + UtilsService.asRegex(settingsPathsPartialRegex,  customizationPathRegex, objectsUpdatePathRegex);
        }

        let administrationPathsPartialList = [
            'persons/dashboard',
            'person/add',
            'email/defaults/dashboard',
            'permissions/(application|user|role)/dashboard'
        ];
        let administrationPathsPartialRegex = UtilsService.asRegex(administrationPathsPartialList);
        let settingsPathRegex = getSettingsPathAsRegex();
        return UtilsService.asRegex(administrationPathsPartialRegex, settingsPathRegex);
    }
    function getNonAdministrationPathAsRegex() {
        function generateApplicationsPathRegex() {
            let applicationPerIdPathList = [
                'dashboard',
                'flows',
                'diagram',
                'change_requests',
                'va',
                'risks',
                'activity_log'];

            let applicationPerIdPathRegex = 'application/' + UtilsService.asRegex('add','\\d+/' + UtilsService.asRegex(applicationPerIdPathList));

            return UtilsService.asRegex('applications/list', applicationPerIdPathRegex);
        }

        function generateEndpointsPathRegex() {
            let endpointPerIdPathList = [
                'dashboard',
                'applications',
                'change_requests',
                'activity_log'];

            let endpointPerIdPathRegex = 'endpoint/' + UtilsService.asRegex('new','\\d+/' + UtilsService.asRegex(endpointPerIdPathList));

            return UtilsService.asRegex('endpoints/list', endpointPerIdPathRegex);
        }

        function generateServicesPathRegex() {
            let servicePerIdPathList = [
                'dashboard',
                'applications',
                'change_requests'];

            let servicePerIdPathRegex = 'service/' + UtilsService.asRegex('new','\\d+/' +  UtilsService.asRegex(servicePerIdPathList));
            return UtilsService.asRegex('services/list', servicePerIdPathRegex);
        }

        function generateProjectsPathRegex() {
            let projectPerIdPathList = [
                'dashboard',
                'reviewAffected',
                'edit',
                'plan'];
            let projectPerIdPathRegex = 'project/\\d+/' + UtilsService.asRegex(projectPerIdPathList);

            let projectsCreatePathPrefixList = [
                'Migration',
                'Decommission',
                'ApplicationMigration',
                'LifeCycleManagement'];
            let projectsCreatePathRegex = UtilsService.asRegex(projectsCreatePathPrefixList) + '/create'
            let projectsPathRegex = 'projects/' + UtilsService.asRegex('dashboard',projectsCreatePathRegex);
            return UtilsService.asRegex(projectPerIdPathRegex, projectsPathRegex);
        }

        let  applicationsPathRegex = generateApplicationsPathRegex();
        let  endpointsPathRegex = generateEndpointsPathRegex();
        let  servicesPathRegex = generateServicesPathRegex();
        let  projectsPathRegex = generateProjectsPathRegex();

        return UtilsService.asRegex(applicationsPathRegex, endpointsPathRegex, servicesPathRegex, projectsPathRegex,'discover');
    }

    let appVizUrlPrefix = '/BusinessFlow/#/';
    let administrationPathRegex = getAdministrationPathAsRegex();
    let nonAdministrationPathRegex = getNonAdministrationPathAsRegex();
    return new RegExp('^' + appVizUrlPrefix + UtilsService.asRegex(administrationPathRegex, nonAdministrationPathRegex,'') + '$');
}

