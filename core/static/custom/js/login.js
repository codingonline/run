$(function(){
	$("#login-form").on('submit', function(e){
		e.preventDefault();
		console.log($(this).serialize());
		var btn = $(this).children("button").button('loading');
		var data = $(this).serialize();
		if($("input[type='checkbox']").is(':checked')){
			data += '&remember=remember';
		}
		$.post("/login?action=login", data, function(data, status){
			console.log(status, data);
			if(data!=""&&data!=null){
				$("#checkpwd").text(data);
			}else{
				window.location.href = "/console";
			}
			btn.button('reset');
		});
	});

	$("input[name='username']").on('blur', function(){
		var username = $(this).val();
		if(username!=""){
			$.get("/login", {action: "isRegistered", username: username}, function(data, status){
				if(data!=""){
					$("#checkemail").html(data);
					disform($("input[name='username']"));
				}else{
					$("#checkemail").html('');
					enform($("input[name='username']"));
				}
			});
		}else{
			$("#checkemail").text("请填写用户名");
			disform($("input[name='username']"));
		}
	});
	
	$("#forget-pwd-btn").on('click', function(e){
		e.preventDefault();
		var _this = $(this);
		var form = _this.parents('form');
		_this.button('loading');
		$.post('/login?action=forget-pwd', form.serialize(), function(data){
			data = $.parseJSON(data);
			_this.button('reset');
			if(data.status=="success"){
				_this.after('<p>邮件已发送至'+data.email+'，请进入邮箱查看</p>');
			}else{
				_this.after('<p>邮件发送失败</p>');
			}
		});
	});

});

function disform(e){
	e.parent().addClass('has-error');
	$("button[type='submit']").attr({"disabled":"disabled"});
}

function enform(e){
	e.parent().removeClass('has-error');
	$("button[type='submit']").removeAttr("disabled");
}
