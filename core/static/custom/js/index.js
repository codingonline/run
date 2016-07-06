/**
 * Created by w2qiao on 2015/7/11.
 */
(function autoLogin(){
	var token = $.cookie('token');
	if(token){
		$.get("/index", {action: "autoLogin"}, function(data, status){
			if(data!='failed'){
				window.location.href = "/console";
			}
		});
	}
}());