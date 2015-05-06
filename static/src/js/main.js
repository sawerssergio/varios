
openerp.pos_kingdom = function(instance) {

    instance.pos_kingdom = {};

    var module = instance.pos_kingdom;

    openerp_pos_db(instance,module);         // import db.js

    openerp_pos_models(instance,module);     // import pos_models.js

    openerp_pos_basewidget(instance,module); // import pos_basewidget.js

    openerp_pos_keyboard(instance,module);   // import  pos_keyboard_widget.js

    openerp_pos_screens(instance,module);    // import pos_screens.js

    openerp_pos_devices(instance,module);    // import pos_devices.js
    
    openerp_pos_widgets(instance,module);    // import pos_widgets.js

    instance.web.client_actions.add('pos.ui', 'instance.pos_kingdom.PosWidget');
};

    
