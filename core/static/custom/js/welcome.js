$(function(){
	$("input[name='username']").on('blur', function(){
		var username = $(this).val();
		$.get("/signup", {action: "isUsernameExisted", username: username}, function(data, status){
			if(data=="true"){
				$("#checkusername").text("用户名已存在");
				disform($("input[name='username']"));
			}else{
				$("#checkusername").text('');
				enform($("input[name='username']"));
			}
		});
	});
	$("input[name='password1']").on('blur', function(){
		var password = $("input[name='password']").val();
		var password1 = $("input[name='password1']").val();
		var checkpwd = $("#checkpwd");
		if(password!=password1){
			checkpwd.text('两次输入密码不一致');
			disform($(this));
		}else{
			checkpwd.text('');
			enform($(this));
		}
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
