$(document).on('change', '#enable-date-edit', function (e) {
	// Get task id which was passed through templates to access specific modal
	const id = $(this).attr('data');
	const dateSwitchClass = '.date-switch-' + id.toString()

	// Enable/disable task form date and time fields when fieldset checkbox is clicked
	$(dateSwitchClass).each(function (element) {
		let elementAttrs = [];
		$.each(this.attributes, function (k, a) {
			elementAttrs.push(a.name)
		});

		// If 'disabled' is an attribute remove it from inputs, else add 'disabled' 
		elementAttrs.indexOf('disabled') > -1 ? $(this).prop('disabled', false) : $(this).prop('disabled', true);
	
	});
});