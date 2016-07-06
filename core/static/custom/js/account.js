(function(){
	$("#set-sae").on('click', function(e){
		var form = $("#sae-form");
		enform(form);
		form[0].reset();
		form.slideToggle();
	});
	$("#cancel-sae").on('click', function(e){
		$("#sae-form").slideUp();
	});
	$("#set-bae").on('click', function(e){
		var form = $("#bae-form");
		enform(form);
		form[0].reset();
		form.slideToggle();
	});
	$("#cancel-bae").on('click', function(e){
		$("#bae-form").slideUp();
	});
	$("#set-email").on('click', function(e){
		var form = $("#email-form");
		enform(form);
		form[0].reset();
		form.slideToggle();
	});
	$("#cancel-email").on('click', function(e){
		$("#email-form").slideUp();
	});
	$("#set-pwd").on('click', function(e){
		var form = $("#pwd-form");
		enform(form);
		form[0].reset();
		form.slideToggle();
	});
	$("#cancel-pwd").on('click', function(e){
		$("#pwd-form").slideUp();
	});
	
	$(document).on('blur', '[type="password"]', function(e){
		var form = $(this).parents('form');
		var pwds = form.find('[type="password"]');
		if($(pwds[0]).val()==$(pwds[1]).val()){
			enform(form);
		}else{
			disform(form, "两次输入密码不一致");
		}
	});
	
	$("#save-pwd").on('click', function(e){
		e.preventDefault();
		var form = $("#pwd-form");
		if(form.find("#pwd1").val()==form.find("#pwd2").val()){
			enform(form);
			$.post('/account?action=save-pwd', form.serialize(), function(data){
				data = $.parseJSON(data);
				if(data.status=="success"){
					form.slideToggle();
					$("#pwd-info").removeClass('text-danger').addClass("text-success").text("新密码设置成功");
				}else if(data.status=="error"){
					$("#pwd-info").removeClass('text-success').addClass("text-danger").text("新密码设置失败");
				}
			});
		}else{
			disform(form, "两次输入密码不一致");
		}
	});
	$("#save-bae").on('click', function(e){
		e.preventDefault();
		var form = $("#bae-form");
		if(form.find('#bae-pwd1').val()==form.find('#bae-pwd2').val()){
			enform(form);
			$.post('/account?action=save-bae', form.serialize(), function(data){
				data = $.parseJSON(data);
				if(data.status=="success"){
					$("#bae").children('span').text(data.unamebaidu);
					$("#set-bae").text('修改');
					form.slideUp();
					$("#bae-info").removeClass('text-danger').addClass("text-success").text('账号设置成功');
				}else{
					$("#bae-info").removeClass('text-success').addClass("text-danger").text('账号设置失败');
				}
			});
		}else{
			disform(form, '两次输入密码不一致');
		}
	});
	$("#save-sae").on('click', function(e){
		e.preventDefault();
		var form = $("#sae-form");
		if(form.find('#sae-pwd1').val()==form.find('#sae-pwd2').val()){
			enform(form);
			$.post('/account?action=save-sae', form.serialize(), function(data){
				data = $.parseJSON(data);
				if(data.status=="success"){
					$("#sae").children('span').text(data.unamesae);
					$("#set-sae").text('修改');
					form.slideUp();
					$("#sae-info").removeClass('text-danger').addClass("text-success").text('账号设置成功');
				}else{
					$("#sae-info").removeClass('text-success').addClass("text-danger").text('账号设置失败');
				}
			});
		}else{
			disform(form, '两次输入密码不一致');
		}
	});
	$("#save-email").on('click', function(e){
		e.preventDefault();
		var form = $("#email-form");
		var _this = $(this);
		_this.button('loading');
		$.post('/account?action=save-email', form.serialize(), function(data){
			data = $.parseJSON(data);
			_this.button('reset');
			if(data.status=="success"){
				form.slideUp();
				$('#email').children('span').text(data.email);
				$("#set-email").text('修改');
				$('#email-info').removeClass('text-danger').addClass("text-success").text('认证邮件已发送，请进入邮箱查看');
			}else{
				$('#email-info').removeClass('text-success').addClass("text-danger").text('认证邮件发送失败');
			}
		});
	});
}());

function disform(e, msg){
	e.children().addClass('has-error');
	e.find(".help-block").text(msg);
	e.find("button[type='submit']").attr({"disabled":"disabled"});
}

function enform(e){
	e.find(".help-block").text("");
	e.children().removeClass('has-error');
	e.find("button[type='submit']").removeAttr("disabled");
}