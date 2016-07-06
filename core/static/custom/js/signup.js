$(function(){
	$("#signup-form").on('submit', function(e){
		e.preventDefault();
		console.log($(this).serialize());
		var btn = $(this).children("button").button('loading');
		var email = $("input[name='email']").val();
		var password = $("input[name='password']").val();
		var reg = /@(.*)/;
		var url = 'http://mail.' + email.match(reg)[1];
		var popup = $("#popemail");
		
		$.post("/signup", $(this).serialize(), function(data, status){
			console.log(status, data);
			if(data=='success'){
				popup.find('p').html("邮件发送成功，<a href=" + url +">点击</a>进入邮箱查看");
				popup.modal("show");
			}else if(data=='error'){
				popup.find('p').text("邮件发送失败：邮箱不存在");
				popup.modal("show");
			}
			btn.button('reset');
		});
		
	
	});
	$("input[name='email']").on('blur', function(){
		var email = $(this).val();
		if(!email.match(/^\w+([-+.]\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$/)){
			$("#checkemail").text('邮箱地址不正确');
			disform($(this));
		}else{
			$.get("/signup", {action: "isActivated", email: email}, function(data, status){
				if(data=="true"){
					$("#checkemail").text('邮箱已注册');
					disform($("input[name='email']"));
				}else{
					$("#checkemail").text('');
					enform($("input[name='email']"));
				}
			});
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
