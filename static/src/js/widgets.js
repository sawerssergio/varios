function openerp_pos_widgets(instance, module){ //module is instance.pos_kingdom
    var QWeb = instance.web.qweb;
	var _t = instance.web._t;

    module.DomCache = instance.web.Class.extend({
        init: function(options){
            options = options || {};
            this.max_size = options.max_size || 2000;

            this.cache = {};
            this.access_time = {};
            this.size = 0;
        },
        cache_node: function(key,node){
            var cached = this.cache[key];
            this.cache[key] = node;
            this.access_time[key] = new Date().getTime();
            if(!cached){
                this.size++;
                while(this.size >= this.max_size){
                    var oldest_key = null;
                    var oldest_time = new Date().getTime();
                    for(var key in this.cache){
                        var time = this.access_time[key];
                        if(time <= oldest_time){
                            oldest_time = time;
                            oldest_key  = key;
                        }
                    }
                    if(oldest_key){
                        delete this.cache[oldest_key];
                        delete this.access_time[oldest_key];
                    }
                    this.size--;
                }
            }
            return node;
        },
        get_node: function(key){
            var cached = this.cache[key];
            if(cached){
                this.access_time[key] = new Date().getTime();
            }
            return cached;
        },
    });

    module.UserWidget = module.PosBaseWidget.extend({
        template:'UserWidget',
        init: function(parent,options){
            var self = this;
            this._super(parent);
        },
        get_image: function(){
            return '/web/binary/image?model=res.partner&id='+this.pos.user.partner_id[0]+'&field=image_small';
        },
        close_session: function(){
        },
        renderElement: function(){
            var self = this;
            this._super();
            this.$(".close").click(function(){
                self.pos_widget.close();
            });
            this.$(".user-image").click(function(event){
                self.$(".user-options").toggleClass('active');
                return false;
            });
        }
    });

    module.NumpadWidget = module.PosBaseWidget.extend({
        template:'NumpadWidget',
        init: function(parent, options) {
            this._super(parent);
            this.state = new module.NumpadState();
            window.numpadstate = this.state;
            var self = this;
        },
        start: function() {
            this.state.bind('change:mode', this.changedMode, this);
            this.changedMode();
            this.$el.find('.numpad-backspace').click(_.bind(this.clickDeleteLastChar, this));
            this.$el.find('.numpad-minus').click(_.bind(this.clickSwitchSign, this));
            this.$el.find('.number-char').click(_.bind(this.clickAppendNewChar, this));
            this.$el.find('.mode-button').click(_.bind(this.clickChangeMode, this));
        },
        clickDeleteLastChar: function() {
            return this.state.deleteLastChar();
        },
        clickSwitchSign: function() {
            return this.state.switchSign();
        },
        clickAppendNewChar: function(event) {
            var newChar;
            newChar = event.currentTarget.innerText || event.currentTarget.textContent;
            return this.state.appendNewChar(newChar);
        },
        clickChangeMode: function(event) {
            var newMode = event.currentTarget.attributes['data-mode'].nodeValue;
            return this.state.changeMode(newMode);
        },
        changedMode: function() {
            var mode = this.state.get('mode');
            $('.selected-mode').removeClass('selected-mode');
            $(_.str.sprintf('.mode-button[data-mode="%s"]', mode), this.$el).addClass('selected-mode');
        },
    });

    // The paypad allows to select the payment method (cashregisters) 
    // used to pay the order.
    module.PaypadWidget = module.PosBaseWidget.extend({
        template: 'PaypadWidget',
        renderElement: function() {
            var self = this;
            this._super();

            _.each(this.pos.cashregisters,function(cashregister) {
                var button = new module.PaypadButtonWidget(self,{
                    pos: self.pos,
                    pos_widget : self.pos_widget,
                    cashregister: cashregister,
                });
                button.appendTo(self.$el);
            });
        }
    });

    module.PaypadButtonWidget = module.PosBaseWidget.extend({
        template: 'PaypadButtonWidget',
        init: function(parent, options){
            this._super(parent, options);
            this.cashregister = options.cashregister;
        },
        renderElement: function() {
            var self = this;
            this._super();

            this.$el.click(function(){
                if (self.pos.get('selectedOrder').get('screen') === 'receipt'){  //TODO Why ?
                    console.warn('TODO should not get there...?');
                    return;
                }
                self.pos.get('selectedOrder').addPaymentline(self.cashregister);
                self.pos_widget.screen_selector.set_current_screen('payment');
            });
        },
    });

    module.OrderWidget = module.PosBaseWidget.extend({
        template:'OrderWidget',
        init: function(parent, options) {
            var self = this;
            this._super(parent,options);
            this.type_of = 'inside';
            this.editable = false;
            this.pos.bind('change:selectedOrder', this.change_selected_order, this);
            this.line_click_handler = function(event){
                if(!self.editable){
                    return;
                }
                if(event.target.className === "product-delete-button") {
                   self.pos.get('selectedOrder').deleteOrderline(this.orderline);
                } else {
                    self.pos.pos_widget.product_screen.product_list_widget.set_deselected_product(); 
                    self.pos.get('selectedOrder').deselectLine();
                    self.pos.get('selectedOrder').selectLine(this.orderline);
                    self.pos_widget.numpad.state.reset();
                    //FIXME this should be on a diferent method
                    self.pos.pos_widget.product_options_widget.edit_options(this.orderline.template,{'quantity':this.orderline.get_quantity_display(), 'details': this.orderline.details });
                    var template_categ = this.orderline.template.pos_categ_id[0];
                    self.pos.pos_widget.product_categories_widget.change_category(template_categ);

                    self.pos.pos_widget.product_screen.product_list_widget.set_selected_product(this.orderline.template.id); 

                    self.pos.pos_widget.product_options_widget.set_editable(true);
                }
            };
            this.client_change_handler = function(event){
                self.update_summary();
            }
            this.bind_order_events();
        },
        enable_numpad: function(){
            this.disable_numpad();  //ensure we don't register the callbacks twice
            this.numpad_state = this.pos_widget.numpad.state;
            if(this.numpad_state){
                this.numpad_state.reset();
                this.numpad_state.bind('set_value',   this.set_value, this);
            }
                    
        },
        disable_numpad: function(){
            if(this.numpad_state){
                this.numpad_state.unbind('set_value',  this.set_value);
                this.numpad_state.reset();
            }
        },
        set_editable: function(editable){
            this.editable = editable;
            if(editable){
                this.enable_numpad();
            }else{
                this.disable_numpad();
                this.pos.get('selectedOrder').deselectLine();
            }
        },
        set_value: function(val) {
        	var order = this.pos.get('selectedOrder');
        	if (this.editable && order.getSelectedLine()) {
                var mode = this.numpad_state.get('mode');
                if( mode === 'quantity'){
                    order.getSelectedLine().set_quantity(val);
                }else if( mode === 'discount'){
                    order.getSelectedLine().set_discount(val);
                }else if( mode === 'price'){
                    order.getSelectedLine().set_unit_price(val);
                }
        	}
        },
        change_selected_order: function() {
            this.bind_order_events();
            this.renderElement();
        },
        bind_order_events: function() {

            var order = this.pos.get('selectedOrder');
                order.unbind('change:client', this.client_change_handler);
                order.bind('change:client', this.client_change_handler);

            var lines = order.get('orderLines');
                lines.unbind();
                lines.bind('add', function(){ 
                        this.numpad_state.reset();
                        this.renderElement(true);
                    },this);
                lines.bind('remove', function(line){
                        this.remove_orderline(line);
                        this.numpad_state.reset();
                        this.update_summary();
                    },this);
                lines.bind('change', function(line){
                        this.rerender_orderline(line);
                        this.update_summary();
                    },this);
        },
        render_orderline: function(orderline){
            var self= this;
            var el_str  = openerp.qweb.render('Orderline',{widget:this, line:orderline}); 
            var el_node = document.createElement('div');
                el_node.innerHTML = _.str.trim(el_str);
                el_node = el_node.childNodes[0];
                el_node.orderline = orderline;
                el_node.addEventListener('click',this.line_click_handler);
            var detail_container = el_node.querySelector('.product-details');
            for(var i = 0,len = orderline.details.length;i<len;i++){
                if(orderline.details[i]['detail']){
                    detail_el_node = this.render_detail({
                        detail_qty: orderline.details[i]['detail_qty'],
                        detail: orderline.details[i]['detail']
                    });
                    detail_container.appendChild(detail_el_node);
                }
            }
            orderline.node = el_node;
            return el_node;
        },
        render_detail: function(options){
            var self = this;
            var el_str = openerp.qweb.render('Linedetail',{
                widget:this, 
                detail_qty: options.detail_qty,
                detail: options.detail
            });
            var el_node = document.createElement('div');
                el_node.innerHTML = _.str.trim(el_str);
                el_node = el_node.childNodes[0];
            return el_node;
        },
        remove_orderline: function(order_line){
            if(this.pos.get('selectedOrder').get('orderLines').length === 0){
                this.renderElement();
            }else{
                order_line.node.parentNode.removeChild(order_line.node);
            }
        },
        rerender_orderline: function(order_line){
            var node = order_line.node;
            var replacement_line = this.render_orderline(order_line);
            if(node.parentNode){
                node.parentNode.replaceChild(replacement_line,node);
            }
        },
        // overriding the openerp framework replace method for performance reasons
        replace: function($target){
            this.renderElement();
            var target = $target[0];
            target.parentNode.replaceChild(this.el,target);
        },
        renderElement: function(scrollbottom){
            var self = this;
            this.pos_widget.numpad.state.reset();

            var order  = this.pos.get('selectedOrder');
            var orderlines = order.get('orderLines').models;

            var el_str  = openerp.qweb.render('OrderWidget',{widget:this, order:order, orderlines:orderlines});

            var el_node = document.createElement('div');
                el_node.innerHTML = _.str.trim(el_str);
                el_node = el_node.childNodes[0];


            var list_container = el_node.querySelector('.orderlines');
            for(var i = 0, len = orderlines.length; i < len; i++){
                var orderline = this.render_orderline(orderlines[i]);
                if(orderlines[i].not_display == undefined){
                    list_container.appendChild(orderline);
                }
            }

            if(this.el && this.el.parentNode){
                this.el.parentNode.replaceChild(el_node,this.el);
            }
            this.el = el_node;
            this.update_summary();

            if(scrollbottom){
                this.el.querySelector('.order-scroller').scrollTop = 100 * orderlines.length;
            }
            this.el.querySelector('.order-restart').addEventListener("click",function(){
                self.pos.get('selectedOrder').restart_order();
            });
            var list_type_of = this.el.querySelectorAll('.type-of');
            for( var i=0; i < list_type_of.length; i++){
                list_type_of[i].addEventListener("click",function(target){
                    if(self.set_type_of(this.classList[0])) {
                        if(self.el
                            .querySelector(".order-type-of>.selected")){
                            self.el
                            .querySelector(".order-type-of>.selected")
                            .classList.remove('selected');
                        }
                        this.classList.add('selected');
                    }
                });
                if(list_type_of[i].classList[0]==="inside"){
                    list_type_of[i].classList.add('selected');
                    self.set_type_of(list_type_of[i].classList[0]);
                }
            }
        },
        update_summary: function(){
            var order = this.pos.get('selectedOrder');
            var total     = order ? order.getTotalTaxIncluded() : 0;
            var taxes     = order ? total - order.getTotalTaxExcluded() : 0;

            this.el.querySelector('.order-summary .total > .subentry-total > .value').textContent = this.format_currency(total);
            //this.el.querySelector('.order-summary .total .subentry .value').textContent = this.format_currency(taxes);

        },
        set_type_of: function(type_of){
            if(this.type_of !== type_of) {
                this.pos.get('selectedOrder').set_type_of(type_of);
                this.type_of = type_of;
                return true;
            }
            return false;
        },
    });

    module.OrderButtonWidget = module.PosBaseWidget.extend({
        template:'OrderButtonWidget',
        init: function(parent, options) {
            this._super(parent,options);
            var self = this;

            this.order = options.order;
            this.order.bind('destroy',this.destroy, this );
            this.order.bind('change', this.renderElement, this );
            this.pos.bind('change:selectedOrder', this.renderElement,this );
        },
        renderElement:function(){
            this.selected = ( this.pos.get('selectedOrder') === this.order )
            this._super();
            var self = this;
            this.$el.click(function(){ 
                if( self.pos.get('selectedOrder') === self.order ){
                    var ss = self.pos.pos_widget.screen_selector;
                    if(ss.get_current_screen() === 'clientlist'){
                        ss.back();
                    }else if (ss.get_current_screen() !== 'receipt'){
                        ss.set_current_screen('clientlist');
                    }
                }else{
                    self.selectOrder();
                }
            });
            if( this.selected){
                this.$el.addClass('selected');
            }
        },
        selectOrder: function(event) {
            this.pos.set({
                selectedOrder: this.order
            });
        },
        destroy: function(){
            this.order.unbind('destroy', this.destroy, this);
            this.order.unbind('change',  this.renderElement, this);
            this.pos.unbind('change:selectedOrder', this.renderElement, this);
            this._super();
        },
    });

    module.ActionButtonWidget = instance.web.Widget.extend({
        template:'ActionButtonWidget',
        icon_template:'ActionButtonWidgetWithIcon',
        init: function(parent, options){
            this._super(parent, options);
            this.label = options.label || 'button';
            this.rightalign = options.rightalign || false;
            this.click_action = options.click;
            this.disabled = options.disabled || false;
            if(options.icon){
                this.icon = options.icon;
                this.template = this.icon_template;
            }
        },
        set_disabled: function(disabled){
            if(this.disabled != disabled){
                this.disabled = !!disabled;
                this.renderElement();
            }
        },
        renderElement: function(){
            this._super();
            if(this.click_action && !this.disabled){
                this.$el.click(_.bind(this.click_action, this));
            }
        },
    });

    module.ActionBarWidget = instance.web.Widget.extend({
        template:'ActionBarWidget',
        init: function(parent, options){
            this._super(parent,options);
            this.button_list = [];
            this.buttons = {};
            this.visibility = {};
        },
        set_element_visible: function(element, visible, action){
            if(visible != this.visibility[element]){
                this.visibility[element] = !!visible;
                if(visible){
                    this.$('.'+element).removeClass('oe_hidden');
                }else{
                    this.$('.'+element).addClass('oe_hidden');
                }
            }
            if(visible && action){
                this.action[element] = action;
                this.$('.'+element).off('click').click(action);
            }
        },
        set_button_disabled: function(name, disabled){
            var b = this.buttons[name];
            if(b){
                b.set_disabled(disabled);
            }
        },
        destroy_buttons:function(){
            for(var i = 0; i < this.button_list.length; i++){
                this.button_list[i].destroy();
            }
            this.button_list = [];
            this.buttons = {};
            return this;
        },
        get_button_count: function(){
            return this.button_list.length;
        },
        add_new_button: function(button_options){
            var button = new module.ActionButtonWidget(this,button_options);
            this.button_list.push(button);
            if(button_options.name){
                this.buttons[button_options.name] = button;
            }
            button.appendTo(this.$('.pos-actionbar-button-list'));
            return button;
        },
        show:function(){
            this.$el.removeClass('oe_hidden');
        },
        hide:function(){
            this.$el.addClass('oe_hidden');
        },
    });

    module.ProductCategoriesWidget = module.PosBaseWidget.extend({
        template: 'ProductCategoriesWidget',
        init: function(parent, options){
            var self = this;
            this._super(parent,options);
            this.product_type = options.product_type || 'all';  // 'all' | 'weightable'
            this.onlyWeightable = options.onlyWeightable || false;
            this.category = this.pos.root_category;
            this.breadcrumb = [];
            this.subcategories = [];
            this.product_list_widget = options.product_list_widget || null;
            this.category_cache = new module.DomCache();
            this.set_category();
            
            this.switch_category_handler = function(event){

                var pos_widget = self.pos.pos_widget;

                if ( pos_widget.screen_selector.get_current_screen() !== "products" ) {
                    pos_widget.screen_selector.set_current_screen('products');
                }
                self.pos.pos_widget.product_options_widget.reset();
                self.product_list_widget.set_deselected_product();
                self.pos.get('selectedOrder').deselectLine();
                //DOMStringMap
                self.set_category(self.pos.db.get_category_by_id(Number(this.dataset['categoryId'])));
                if(self.el.querySelector(".categories-list > .selected")){
                    self.el.querySelector(".categories-list > .selected").classList.remove('selected');
                }
                self.el.querySelector("[data-category-id='"+this.dataset['categoryId']+"']").classList.add('selected');
                //FIXME [KINGDOM][VD] This should be separated into another method of this widget.
                var products = self.pos.db.get_template_by_category(self.category.id);
                self.product_list_widget.set_product_list(products);
                //self.renderElement();
            };
            
            this.clear_search_handler = function(event){
                self.clear_search();
            };

            var search_timeout  = null;
            this.search_handler = function(event){
                clearTimeout(search_timeout);

                var query = this.value;

                search_timeout = setTimeout(function(){
                    self.perform_search(self.category, query, event.which === 13);
                },70);
            };
        },
        change_category: function(category_id){
            var category = this.pos.db.get_category_by_id(category_id);
            this.set_category(category);
            var templates = this.pos.db.get_template_by_category(category_id);
            this.product_list_widget.set_product_list(templates);
            //set selected product
        },
        // changes the category. if undefined, sets to root category
        set_category : function(category){
            var db = this.pos.db;
            if(!category){
                this.category = db.get_category_by_id(db.root_category_id);
            }else{
                this.category = category;
            }
            this.breadcrumb = [];
            var ancestors_ids = db.get_category_ancestors_ids(this.category.id);
            for(var i = 1; i < ancestors_ids.length; i++){
                this.breadcrumb.push(db.get_category_by_id(ancestors_ids[i]));
            }
            if(this.category.id !== db.root_category_id){
                this.breadcrumb.push(this.category);
            }

            this.subcategories = db.get_category_by_id(db.get_category_childs_ids(this.category.id));
        },

        get_image_url: function(category){
            return window.location.origin + '/web/binary/image?model=pos.category&field=image_medium&id='+category.id;
        },

        render_category: function( category, with_image ){
            var cached = this.category_cache.get_node(category.id);
            if(!cached){
                if(with_image){
                    var image_url = this.get_image_url(category);
                    var category_html = QWeb.render('CategoryButton',{ 
                            widget:  this, 
                            category: category, 
                            image_url: this.get_image_url(category),
                        });
                        category_html = _.str.trim(category_html);
                    var category_node = document.createElement('div');
                        category_node.innerHTML = category_html;
                        category_node = category_node.childNodes[0];
                }else{
                    var category_html = QWeb.render('CategorySimpleButton',{ 
                            widget:  this, 
                            category: category, 
                        });
                        category_html = _.str.trim(category_html);
                    var category_node = document.createElement('div');
                        category_node.innerHTML = category_html;
                        category_node = category_node.childNodes[0];
                }
                this.category_cache.cache_node(category.id,category_node);
                return category_node;
            }
            return cached; 
        },

        replace: function($target){
            this.renderElement();
            var target = $target[0];
            target.parentNode.replaceChild(this.el,target);
        },

        renderElement: function(){
            var self = this;

            var el_str  = openerp.qweb.render(this.template, {widget: this});
            var el_node = document.createElement('div');
                el_node.innerHTML = el_str;
                el_node = el_node.childNodes[1];

            if(this.el && this.el.parentNode){
                this.el.parentNode.replaceChild(el_node,this.el);
            }

            this.el = el_node;

            var hasimages = false;  //if none of the subcategories have images, we don't display buttons with icons
            for(var i = 0; i < this.subcategories.length; i++){
                if(this.subcategories[i].image){
                    hasimages = true;
                    break;
                }
            }

            var list_container = el_node.querySelector('.categories-list');
            if (list_container) { 
                if (!hasimages) {
                    list_container.classList.add('simple');
                } else {
                    list_container.classList.remove('simple');
                }
                for(var i = 0, len = this.subcategories.length; i < len; i++){
                    list_container.appendChild(this.render_category(this.subcategories[i],hasimages));
                };
            }

            var buttons = el_node.querySelectorAll('.js-category-switch');
            for(var i = 0; i < buttons.length; i++){
                buttons[i].addEventListener('click',this.switch_category_handler);
            }

            var products = this.pos.db.get_template_by_category(this.category.id);
            this.product_list_widget.set_product_list(products);

            //this.el.querySelector('.searchbox input').addEventListener('keyup',this.search_handler);

            //this.el.querySelector('.search-clear').addEventListener('click',this.clear_search_handler);

            //if(this.pos.config.iface_vkeyboard && this.pos_widget.onscreen_keyboard){
                //this.pos_widget.onscreen_keyboard.connect($(this.el.querySelector('.searchbox input')));
            //}
        },
        
        // resets the current category to the root category
        reset_category: function(){
            this.set_category();
            this.renderElement();
        },

        // empties the content of the search box
        clear_search: function(){
            var products = this.pos.db.get_product_by_category(this.category.id);
            this.product_list_widget.set_product_list(products);
            var input = this.el.querySelector('.searchbox input');
                input.value = '';
                input.focus();
        },
        perform_search: function(category, query, buy_result){
            if(query){
                var products = this.pos.db.search_product_in_category(category.id,query)
                if(buy_result && products.length === 1){
                        this.pos.get('selectedOrder').addProduct(products[0]);
                        this.clear_search();
                }else{
                    this.product_list_widget.set_product_list(products);
                }
            }else{
                var products = this.pos.db.get_product_by_category(this.category.id);
                this.product_list_widget.set_product_list(products);
            }
        },

    });

    module.ProductListWidget = module.PosBaseWidget.extend({
        template:'ProductListWidget',
        init: function(parent, options) {
            var self = this;
            this._super(parent,options);
            this.model = options.model;
            this.productwidgets = [];
            this.weight = options.weight || 0;
            this.show_scale = options.show_scale || false;
            this.next_screen = options.next_screen || false;

            this.click_product_handler = function(event){
                var product = self.pos.db.get_template_by_id(this.dataset['productId']);
                options.click_product_action(product);
            };

            this.product_list = options.product_list || [];
            this.product_cache = new module.DomCache();
        },
        set_product_list: function(product_list){
            this.product_list = product_list;
            this.renderElement();
        },
        set_deselected_product: function(){
            if(this.selected_product_id){ 
                this.el.querySelector("[data-product-id='"+this.selected_product_id+"'] > .product-img").className = 'product-img';
                this.selected_product_id = undefined; 
            }
        },
        set_selected_product:function(id){
            /*var products = this.el.querySelectorAll('.product');
            for(var i = 0;i<products.length;i++){
                var product_id = Number(products[i].attributes[0].value);
                    products[i].querySelector('.product-img').className = "product-img";
                if(id == product_id){
                    products[i].querySelector('.product-img').className = "product-img selected";
                }
            }*/
            this.selected_product_id = id; 
            this.el.querySelector("[data-product-id='"+id+"'] > .product-img").className += ' selected-product'; 
        },
        get_product_image_url: function(product){
            return window.location.origin + '/web/binary/image?model=product.product&field=image&id='+product.id;
        },
        get_template_image_url: function(template) {
            return window.location.origin + '/web/binary/image?model=product.template&field=image&id='+template.id;
        },
        replace: function($target){
            this.renderElement();
            var target = $target[0];
            target.parentNode.replaceChild(this.el,target);
        },
        render_product: function(product){
            var cached = this.product_cache.get_node(product.id);
            if(!cached){
                var image_url = this.get_template_image_url(product);
                var product_html = QWeb.render('Product',{ 
                        widget:  this, 
                        product: product, 
                        image_url: image_url,
                    });
                var product_node = document.createElement('div');
                product_node.innerHTML = product_html;
                product_node = product_node.childNodes[1];
                this.product_cache.cache_node(product.id,product_node);
                return product_node;
            }
            return cached;
        },

        renderElement: function() {
            var self = this;

            // this._super()
            var el_str  = openerp.qweb.render(this.template, {widget: this});
            var el_node = document.createElement('div');
                el_node.innerHTML = el_str;
                el_node = el_node.childNodes[1];
            var product_tmpl_id = -1;
            if(this.el && this.el.parentNode){
                this.el.parentNode.replaceChild(el_node,this.el);
            }
            this.el = el_node;

            var list_container = el_node.querySelector('.product-list');
            for(var i = 0, len = this.product_list.length; i < len; i++){
                product_tmpl_id = this.product_list[i].product_tmpl_id;
                var product_node = this.render_product(this.product_list[i]);
                product_node.addEventListener('click',this.click_product_handler);
                list_container.appendChild(product_node);
            };
        },
    });

    module.DestinationSelectorWidget = module.PosBaseWidget.extend({
        template: 'DestinationSelectorWidget',
        init: function(parent, options){
            var self = this;
            this._super(parent, options);
            this.destinations = this.pos.db.destination_by_id;
            this.destination_selected = Object.keys(this.pos.db.destination_by_id)[0];
            this.was_shown = false;
        },
        start: function(){
            this._super();
            this.hide();
        },
        renderElement: function(){
            var self = this;
            this._super();
            var el_str  = openerp.qweb.render('DestinationSelectorWidget',{widget:this});

            var el_node = document.createElement('div');
                el_node.innerHTML = _.str.trim(el_str);
                el_node = el_node.childNodes[0];

            if(this.el && this.el.parentNode){
                this.el.parentNode.replaceChild(el_node,this.el);
            }

            this.el = el_node;

            this.$el = $(this.el);

            var value_container = el_node.querySelector('.destination-list');
            for(var destination in this.destinations){
                var destination = this.destinations[destination];
                var is_selected = this.is_destination_selected(destination);
                var value_html = QWeb.render('Destination',{ 
                        widget:  this, 
                        destination: destination, 
                        is_selected: is_selected,
                    });
                var value_node = document.createElement('div');
                value_node.innerHTML = value_html;
                value_node = value_node.childNodes[1];
                value_node.addEventListener('click', function(event) {
                    self.destination_selected = this.dataset['destinationId'];
                    self.save_destination();
                    self.renderElement();
                });
                value_container.appendChild(value_node);
            }
        },
        save_destination: function(){
            var destination = this.pos.db.get_destination_by_id(this.destination_selected);
            this.pos.get('selectedOrder').set_destination(destination);
        },
        is_destination_selected: function(destination){
            return Number(this.destination_selected) === destination.id;
        },
        only_one_destination: function(){
            if(_.size(this.destinations) === 1){
                this.save_destination();
                return true;
            } else {
                //[FIXME] this should be shown diferently.
                //It should not return any value show function.
                return this.show();
            }
        },
        show:function(){
            this.$el.removeClass('oe_hidden');
            this.was_shown = !this.was_shown;
            return !this.was_shown;
        },
        hide:function(){
            this.$el.addClass('oe_hidden');
            this.save_destination();
        },
    });

    module.ProductOptionsWidget = module.PosBaseWidget.extend({
        template: 'ProductOptionsWidget',
        init: function(parent, options) {
            var self = this;
            var options = options || {};
            this._super(parent, options);
            this.total_quantity = options.total_quantity || 1;
            this.selected_template = undefined;
            this.editable = false;
            this.attributes = {};
            this.click_value_handler = function(event){
                var className = event.target.className;

                if(!className) {
                    className = event.target.parentNode.className;
                }
                var value_id = this.dataset['valueId'];
                if(!self.attributes[value_id]){
                    self.attributes[value_id] = 0;
                }

                if(className === "block-increase"){
                    self.set_value(value_id,1);
                } else if(className === "block-decrease" && self.attributes[value_id] > 0) {
                    self.set_value(value_id,-1);
                } else if(className === "block-quantity"){
                    self.pos_widget.onscreen_keyboard.connect( self.$( event.target ), event.target.getAttribute('type'), function(){
                        self.pos_widget.onscreen_keyboard.hide();
                    });
                }
            };
            this.value_cache = new module.DomCache();
        },
        start: function(){
            var self = this;
            this.hide();
        },
        //When you want to increase or decrease the value, do not pass the third
        //parameter. Or when you want to set the value, pass the third parameter 
        //as true.
        set_value: function(id, value, is_set){
            //if(!this.attributes[id] && is_set) {
            //    this.attributes[id]=0;
            //}
            if(is_set){
                if(this.attributes[id]){
                this.set_total_quantity(this.total_quantity-this.attributes[id]+value);
                this.attributes[id] = value;
                } else {
                    this.attributes[id] = value;
                    this.set_total_quantity(value);
                }
            } else {
                this.attributes[id] += value;
                this.set_total_quantity(this.total_quantity+value);
            }
            this.el.querySelector("[data-value-id='"+id+"'] > .top-block > .block-quantity").value = this.attributes[id];
        },
        set_total_quantity: function(value){
            this.total_quantity = value;
            this.el.querySelector(".block-selection > .bottom-block > .total-quantity").textContent = this.total_quantity;
        },
        set_editable: function(bool){
            this.editable = bool;
        },
        edit_options:function(template,options){
            var self = this;
            this.editable = true;
            this.selected_template = template;
            this.attributes = {};
            this.renderElement();
            if(this.selected_template.line){
                options.details.forEach(function(detail){
                    self.set_value(detail.id,detail.detail_qty,true);
                });
            }else{
                self.set_value(this.selected_template.id,options.quantity,true);
            }
            this.set_total_quantity(options.quantity);
            this.show();
        },
        set_template:function(product_template){
            if(product_template == this.selected_template){
                //[FIXME] [KINGDOM] this process should be reversed,
                //first call to total quantity and then value.
                if (Object.keys(this.attributes).length === 0) {
                    this.set_total_quantity(this.total_quantity+1);
                    this.el.querySelector("[data-value-id='"+this.selected_template.id+"'] > .top-block > .block-quantity").value = this.total_quantity;
                    return;
                }
                this.set_value(Object.keys(this.attributes)[0],1);
            }else{
                this.selected_template = product_template;
                this.attributes = {};
                this.total_quantity = 0;
                this.renderElement();
                this.show();
            }
        },
        get_product_image_url: function(){
            if(this.selected_template) {
            return window.location.origin + '/web/binary/image?model=product.template&field=image&id='+this.selected_template.id;
            } else {
                return undefined;
            }
        },
        get_attribute_value_image_url: function(id){
            return window.location.origin + '/web/binary/image?model=product.attribute.value&field=image&id='+id;
        },
        clear_attribute: function(id) {
            this.attributes[id] = 0;
            this.el.querySelector("[data-value-id='"+id+"'] > .top-block > .block-quantity").value = 0;
        },
        replace: function($target){
            this.renderElement();
            var target = $target[0];
            target.parentNode.replaceChild(this.el,target);
        },
        render_value: function(value){
            var self = this;
            var cached = this.value_cache.get_node(value.id);
            if(!cached){
                var image_url = this.get_attribute_value_image_url(value.id);
                var value_html = QWeb.render('Value',{ 
                        widget:  this, 
                        value: value, 
                        image_url: image_url,
                    });
                var value_node = document.createElement('div');
                value_node.innerHTML = value_html;
                value_node = value_node.childNodes[1];
                $(value_node).find('.block-quantity').on('keyup',function(event){
                    self.set_value(value.id,Number(event.target.value), true);
                });
                this.value_cache.cache_node(value.id,value_node);
                return value_node;
            }
            return cached;
        },
        renderElement: function(){
            var self = this;
            var image_url = this.get_product_image_url();
            var el_str  = openerp.qweb.render('ProductOptionsWidget',{widget:this, image_url:image_url});

            var el_node = document.createElement('div');
                el_node.innerHTML = _.str.trim(el_str);
                el_node = el_node.childNodes[0];

            if(this.el && this.el.parentNode){
                this.el.parentNode.replaceChild(el_node,this.el);
            }

            this.el = el_node;

            this.$el = $(this.el);

            var value_container = el_node.querySelector('.values-list');
            if(self.selected_template){
                if(!self.selected_template.line){
                    var value_html = QWeb.render('Value',{ 
                            widget:  this, 
                            value: {id:this.selected_template.id}, 
                            image_url: self.get_product_image_url(),
                        });
                    var value_node = document.createElement('div');
                    value_node.innerHTML = value_html;
                    value_node = value_node.childNodes[1];
                    $(value_node).find('.block-quantity').on('keyup',function(event){
                        self.set_value(self.selected_template.id,Number(event.target.value), true);
                    });
                    value_node.addEventListener('click', function(event) {
                        var className = event.target.className;

                        if(!className) {
                            className = event.target.parentNode.className;
                        }

                        if(className === "block-increase"){
                            self.set_total_quantity(self.total_quantity+1);
                        } else if(className === "block-decrease" && self.total_quantity > 0) {
                            self.set_total_quantity(self.total_quantity-1);
                        } else if(className === "block-quantity"){
                            self.pos_widget.onscreen_keyboard.connect( self.$( event.target ), event.target.getAttribute('type'), function(){
                                self.pos_widget.onscreen_keyboard.hide();
                            });
                        }
                        self.el.querySelector("[data-value-id='"+this.dataset['valueId']+"'] > .top-block > .block-quantity").value = self.total_quantity;
                    });
                    value_container.appendChild(value_node);
                }
                for(var line in self.selected_template.line) {
                    for(var i = 0, len = this.selected_template.line[line].length; i < len; i++){
                        var value_tmpl = self.pos.db.get_attribute_value_by_id(this.selected_template.line[line][i]);
                        //[FIXME] [KINGDOM] this should be with a variable of the widget and not zero number. Not work in Edit Order.

                        var value_node = this.render_value(value_tmpl);
                        value_node.addEventListener('click',this.click_value_handler);
                        value_container.appendChild(value_node);
                        self.clear_attribute(value_tmpl.id);
                    };
                }
            }
            this.hide();
        },
        checkAction: function(){
            var self = this;
            if(!self.editable){
                this.add_template_order(self.selected_template);
                if(self.selected_template.is_combo){
                    self.pos.pos_widget.product_screen.product_list_widget.set_deselected_product(); 
                    var drinks_categ_id = 2;
                    self.pos.get('selectedOrder').set_screen_data('drinks_to_discount',self.total_quantity);
                    self.pos.pos_widget.product_categories_widget.change_category(drinks_categ_id);
                }
            }else{
                self.edit_line_order(self.pos.get('selectedOrder').selected_orderline);
            }
            self.reset();
        },
        show:function(){
            this.$el.removeClass('oe_hidden');
        },
        hide:function(){
            this.$el.addClass('oe_hidden');
        },
        edit_line_order:function(orderline){
            if(orderline.template.line){
                orderline.edit_details(this.attributes);
                orderline.set_total_quantity();
            }else{
                orderline.set_quantity(this.total_quantity);
                orderline.set_quantity_display(this.total_quantity);
                
                if(orderline.quantity == 0){
                    this.pos.get('selectedOrder').removeOrderline(orderline);
                }
            }
            this.pos.pos_widget.order_widget.rerender_orderline(orderline);
            this.editable = false;
        },
        add_template_order:function(product_template,attrs){
            var attributes = attrs || this.attributes;
            var self = this;
            var products = this.pos.db.get_product_by_template(this.selected_template.id);
            if(product_template.line){
                for(value_id in attributes){
                    if(attributes[value_id]>0){
                        product_list = products.filter(function(product){
                            return product.attribute_value_ids[0] == value_id;
                        });
                        var value = this.pos.db.get_attribute_value_by_id(value_id);
                        self.pos.get('selectedOrder').addProduct(product_list[0],{
                            template: product_template,
                            value: value,
                            attributes: attributes,
                            quantity: attributes[value_id]
                        });
                    }
                }
            }else{
                this.pos.get('selectedOrder').addProduct(products[0],{
                    template: product_template,
                    quantity: this.total_quantity
                });
            }
        },
        reset: function(){
            this.attributes = {};
            this.selected_template = undefined;
            this.hide();
        },
        is_content: function(){
            return this.selected_template !== undefined;
        }
    });

    module.InvoiceOptionWidget = module.PosBaseWidget.extend({
        template: 'InvoiceOptionWidget',
        init: function(parent, options){
            var options = options || {};
            this._super(parent, options);
            this.currency = options.currency || 'bob';// bob || usd
            //meson or mezzanine
            this.intend_for = options.intend_for || 'ms'; // ms || mz 
            this.hide();
        },
        show:function(){
            this.$el.removeClass('oe_hidden');
        },
        hide:function(){
            this.$el.addClass('oe_hidden');
        },
    });

    module.UsernameWidget = module.PosBaseWidget.extend({
        template: 'UsernameWidget',
        init: function(parent, options){
            var options = options || {};
            this._super(parent,options);
            this.mode = options.mode || 'cashier';
        },
        set_user_mode: function(mode){
            this.mode = mode;
            this.refresh();
        },
        refresh: function(){
            this.renderElement();
        },
        get_name: function(){
            var user;
            if(this.mode === 'cashier'){
                user = this.pos.cashier || this.pos.user;
            }else{
                user = this.pos.get('selectedOrder').get_client()  || this.pos.user;
            }
            if(user){
                return user.name;
            }else{
                return "";
            }
        },
        get_image: function(){
            return '/web/binary/image?model=res.partner&id='+this.pos.user.partner_id[0]+'&field=image_small';
        },
    });

    module.HeaderButtonWidget = module.PosBaseWidget.extend({
        template: 'HeaderButtonWidget',
        init: function(parent, options){
            options = options || {};
            this._super(parent, options);
            this.action = options.action;
            this.label   = options.label;
        },
        renderElement: function(){
            var self = this;
            this._super();
            if(this.action){
                this.$el.click(function(){
                    self.action();
                });
            }
        },
        show: function(){ this.$el.removeClass('oe_hidden'); },
        hide: function(){ this.$el.addClass('oe_hidden'); },
    });

    // The debug widget lets the user control and monitor the hardware and software status
    // without the use of the proxy
    module.DebugWidget = module.PosBaseWidget.extend({
        template: "DebugWidget",
        eans:{
            admin_badge:  '0410100000006',
            client_badge: '0420200000004',
            invalid_ean:  '1232456',
            soda_33cl:    '5449000000996',
            oranges_kg:   '2100002031410',
            lemon_price:  '2301000001560',
            unknown_product: '9900000000004',
        },
        events:[
            'open_cashbox',
            'print_receipt',
            'scale_read',
        ],
        minimized: false,
        init: function(parent,options){
            this._super(parent,options);
            var self = this;
            
            this.minimized = false;

            // for dragging the debug widget around
            this.dragging  = false;
            this.dragpos = {x:0, y:0};

            function eventpos(event){
                if(event.touches && event.touches[0]){
                    return {x: event.touches[0].screenX, y: event.touches[0].screenY};
                }else{
                    return {x: event.screenX, y: event.screenY};
                }
            }

            this.dragend_handler = function(event){
                self.dragging = false;
            };
            this.dragstart_handler = function(event){
                self.dragging = true;
                self.dragpos = eventpos(event);
            };
            this.dragmove_handler = function(event){
                if(self.dragging){
                    var top = this.offsetTop;
                    var left = this.offsetLeft;
                    var pos  = eventpos(event);
                    var dx   = pos.x - self.dragpos.x; 
                    var dy   = pos.y - self.dragpos.y; 

                    self.dragpos = pos;

                    this.style.right = 'auto';
                    this.style.bottom = 'auto';
                    this.style.left = left + dx + 'px';
                    this.style.top  = top  + dy + 'px';
                }
                event.preventDefault();
                event.stopPropagation();
            };
        },
        start: function(){
            var self = this;

            this.el.addEventListener('mouseleave', this.dragend_handler);
            this.el.addEventListener('mouseup',    this.dragend_handler);
            this.el.addEventListener('touchend',   this.dragend_handler);
            this.el.addEventListener('touchcancel',this.dragend_handler);
            this.el.addEventListener('mousedown',  this.dragstart_handler);
            this.el.addEventListener('touchstart', this.dragstart_handler);
            this.el.addEventListener('mousemove',  this.dragmove_handler);
            this.el.addEventListener('touchmove',  this.dragmove_handler);

            this.$('.toggle').click(function(){
                var content = self.$('.content');
                var bg      = self.$el;
                if(!self.minimized){
                    content.animate({'height':'0'},200);
                }else{
                    content.css({'height':'auto'});
                }
                self.minimized = !self.minimized;
            });
            this.$('.button.set_weight').click(function(){
                var kg = Number(self.$('input.weight').val());
                if(!isNaN(kg)){
                    self.pos.proxy.debug_set_weight(kg);
                }
            });
            this.$('.button.reset_weight').click(function(){
                self.$('input.weight').val('');
                self.pos.proxy.debug_reset_weight();
            });
            this.$('.button.custom_ean').click(function(){
                var ean = self.pos.barcode_reader.sanitize_ean(self.$('input.ean').val() || '0');
                self.$('input.ean').val(ean);
                self.pos.barcode_reader.scan(ean);
            });
            this.$('.button.reference').click(function(){
                self.pos.barcode_reader.scan(self.$('input.ean').val());
            });
            this.$('.button.show_orders').click(function(){
                self.pos.pos_widget.screen_selector.show_popup('unsent-orders');
            });
            this.$('.button.delete_orders').click(function(){
                self.pos.pos_widget.screen_selector.show_popup('confirm',{
                    message: _t('Delete Unsent Orders ?'),
                    comment: _t('This operation will permanently destroy all unsent orders from the local storage. You will lose all the data. This operation cannot be undone.'),
                    confirm: function(){
                        self.pos.db.remove_all_orders();
                        self.pos.set({synch: { state:'connected', pending: 0 }});
                    },
                });
            });
            _.each(this.eans, function(ean, name){
                self.$('.button.'+name).click(function(){
                    self.$('input.ean').val(ean);
                    self.pos.barcode_reader.scan(ean);
                });
            });
            _.each(this.events, function(name){
                self.pos.proxy.add_notification(name,function(){
                    self.$('.event.'+name).stop().clearQueue().css({'background-color':'#6CD11D'}); 
                    self.$('.event.'+name).animate({'background-color':'#1E1E1E'},2000);
                });
            });
        },
    });

// ---------- Main Point of Sale Widget ----------

    module.StatusWidget = module.PosBaseWidget.extend({
        status: ['connected','connecting','disconnected','warning'],
        set_status: function(status,msg){
            var self = this;
            for(var i = 0; i < this.status.length; i++){
                this.$('.js_'+this.status[i]).addClass('oe_hidden');
            }
            this.$('.js_'+status).removeClass('oe_hidden');
            
            if(msg){
                this.$('.js_msg').removeClass('oe_hidden').html(msg);
            }else{
                this.$('.js_msg').addClass('oe_hidden').html('');
            }
        },
    });

    // this is used to notify the user that data is being synchronized on the network
    module.SynchNotificationWidget = module.StatusWidget.extend({
        template: 'SynchNotificationWidget',
        start: function(){
            var self = this;
            this.pos.bind('change:synch', function(pos,synch){
                self.set_status(synch.state, synch.pending);
            });
            this.$el.click(function(){
                self.pos.push_order();
            });
        },
    });

    // this is used to notify the user if the pos is connected to the proxy
    module.ProxyStatusWidget = module.StatusWidget.extend({
        template: 'ProxyStatusWidget',
        set_smart_status: function(status){
            if(status.status === 'connected'){
                var warning = false;
                var msg = ''
                if(this.pos.config.iface_scan_via_proxy){
                    var scanner = status.drivers.scanner ? status.drivers.scanner.status : false;
                    if( scanner != 'connected' && scanner != 'connecting'){
                        warning = true;
                        msg += _t('Scanner');
                    }
                }
                if( this.pos.config.iface_print_via_proxy || 
                    this.pos.config.iface_cashdrawer ){
                    var printer = status.drivers.escpos ? status.drivers.escpos.status : false;
                    if( printer != 'connected' && printer != 'connecting'){
                        warning = true;
                        msg = msg ? msg + ' & ' : msg;
                        msg += _t('Printer');
                    }
                }
                if( this.pos.config.iface_electronic_scale ){
                    var scale = status.drivers.scale ? status.drivers.scale.status : false;
                    if( scale != 'connected' && scale != 'connecting' ){
                        warning = true;
                        msg = msg ? msg + ' & ' : msg;
                        msg += _t('Scale');
                    }
                }
                msg = msg ? msg + ' ' + _t('Offline') : msg;
                this.set_status(warning ? 'warning' : 'connected', msg);
            }else{
                this.set_status(status.status,'');
            }
        },
        start: function(){
            var self = this;
            
            this.set_smart_status(this.pos.proxy.get('status'));

            this.pos.proxy.on('change:status',this,function(eh,status){ //FIXME remove duplicate changes 
                self.set_smart_status(status.newValue);
            });

            this.$el.click(function(){
                self.pos.connect_to_proxy();
            });
        },
    });


    // The PosWidget is the main widget that contains all other widgets in the PointOfSale.
    // It is mainly composed of :
    // - a header, containing the list of orders
    // - a leftpane, containing the list of bought products (orderlines) 
    // - a rightpane, containing the screens (see pos_screens.js)
    // - an actionbar on the bottom, containing various action buttons
    // - popups
    // - an onscreen keyboard
    // a screen_selector which controls the switching between screens and the showing/closing of popups

    module.PosWidget = module.PosBaseWidget.extend({
        template: 'PosWidget',
        init: function() {
            this._super(arguments[0],{});

            this.pos = new module.PosModel(this.session,{pos_widget:this});
            this.pos_widget = this; //So that pos_widget's childs have pos_widget set automatically

            this.numpad_visible = false;
            this.leftpane_visible = true;
            this.leftpane_width   = '440px';
            this.cashier_controls_visible = true;

            FastClick.attach(document.body);
        },

        disable_rubberbanding: function(){
            // prevent the pos body from being scrollable. 
            document.body.addEventListener('touchmove',function(event){
                var node = event.target;
                while(node){
                    if(node.classList && node.classList.contains('touch-scrollable')){
                        return;
                    }
                    node = node.parentNode;
                }
                event.preventDefault();
            });
        },

        start: function() {
            this._super(arguments[0],{});
            var self = this;
            window.is_mobile = false;
            if( /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ) {
                window.is_mobile = true;
            }
            return self.pos.ready.done(function() {
                // remove default webclient handlers that induce click delay
                $(document).off();
                $(window).off();
                $('html').off();
                $('body').off();
                $(self.$el).parent().off();
                $('document').off();
                $('.oe_web_client').off();
                $('.openerp_webclient_container').off();

                self.renderElement();
                
                self.$('.neworder-button').click(function(){
                    self.pos.add_new_order();
                });

                self.$('.deleteorder-button').click(function(){
                    if( !self.pos.get('selectedOrder').is_empty() ){
                        self.screen_selector.show_popup('confirm',{
                            message: _t('Destroy Current Order ?'),
                            comment: _t('You will lose any data associated with the current order'),
                            confirm: function(){
                                self.pos.delete_current_order();
                            },
                        });
                    }else{
                        self.pos.delete_current_order();
                    }
                });
                
                //when a new order is created, add an order button widget
                self.pos.get('orders').bind('add', function(new_order){
                    var new_order_button = new module.OrderButtonWidget(null, {
                        order: new_order,
                        pos: self.pos
                    });
                    new_order_button.appendTo(this.$('.orders'));
                    new_order_button.selectOrder();
                }, self);


                self.pos.add_new_order();

                self.build_widgets();

                if(self.pos.config.iface_big_scrollbars){
                    self.$el.addClass('big-scrollbars');
                }

                self.screen_selector.set_default_screen();

                self.pos.barcode_reader.connect();

                instance.webclient.set_content_full_screen(true);

                self.$('.loader').animate({opacity:0},1500,'swing',function(){self.$('.loader').addClass('oe_hidden');});

                self.pos.push_order();

            }).fail(function(err){   // error when loading models data from the backend
                self.loading_error(err);
            });
        },
        loading_error: function(err){
            var self = this;

            var message = err.message;
            var comment = err.stack;

            if(err.message === 'XmlHttpRequestError '){
                message = 'Network Failure (XmlHttpRequestError)';
                comment = 'The Point of Sale could not be loaded due to a network problem.\n Please check your internet connection.';
            }else if(err.message === 'OpenERP Server Error'){
                message = err.data.message;
                comment = err.data.debug;
            }

            if( typeof comment !== 'string' ){
                comment = 'Traceback not available.';
            }

            var popup = $(QWeb.render('ErrorTracebackPopupWidget',{
                widget: { message: message, comment: comment },
            }));

            popup.find('.button').click(function(){
                self.close();
            });

            popup.css({ zindex: 9001 });

            popup.appendTo(this.$el);
        },
        loading_progress: function(fac){
            this.$('.loader .loader-feedback').removeClass('oe_hidden');
            this.$('.loader .progress').css({'width': ''+Math.floor(fac*100)+'%'});
        },
        loading_message: function(msg,progress){
            this.$('.loader .loader-feedback').removeClass('oe_hidden');
            this.$('.loader .message').text(msg);
            if(typeof progress !== 'undefined'){
                this.loading_progress(progress);
            }
        },
        loading_skip: function(callback){
            if(callback){
                this.$('.loader .loader-feedback').removeClass('oe_hidden');
                this.$('.loader .button.skip').removeClass('oe_hidden');
                this.$('.loader .button.skip').off('click');
                this.$('.loader .button.skip').click(callback);
            }else{
                this.$('.loader .button.skip').addClass('oe_hidden');
            }
        },
        // This method instantiates all the screens, widgets, etc. If you want to add new screens change the
        // startup screen, etc, override this method.
        build_widgets: function() {
            var self = this;
            // --------  Screens ---------

            this.product_screen = new module.ProductScreenWidget(this,{});
            this.product_screen.appendTo(this.$('.screens'));

            this.receipt_screen = new module.ReceiptScreenWidget(this, {});
            this.receipt_screen.appendTo(this.$('.screens'));

            this.payment_screen = new module.PaymentScreenWidget(this, {});
            this.payment_screen.appendTo(this.$('.screens'));

            this.clientlist_screen = new module.ClientListScreenWidget(this, {});
            this.clientlist_screen.appendTo(this.$('.screens'));

            this.scale_screen = new module.ScaleScreenWidget(this,{});
            this.scale_screen.appendTo(this.$('.screens'));

            this.client_screen = new module.ClientScreenWidget(this,{});
            this.client_screen.appendTo(this.$('.screens'));

            this.invoice_screen = new module.InvoiceScreenWidget(this,{});
            this.invoice_screen.appendTo(this.$('.screens'));

            // -------- Widgets Kingdom --------
            this.product_categories_widget = new module.ProductCategoriesWidget(this, {
                product_list_widget: this.product_screen.product_list_widget,
            });
            this.product_categories_widget.replace(this.$('.placeholder-ProductCategoriesWidget'));
            this.product_options_widget = new module.ProductOptionsWidget(this, {
                pos : self.pos,
            });
            this.product_options_widget.replace(this.$('.placeholder-order-selector'));

            //this.destination_selector_widget = new module.DestinationSelectorWidget(this, {});
            //this.destination_selector_widget.replace(this.$('.placeholder-destination-selector'));

            // --------  Popups ---------

            this.error_popup = new module.ErrorPopupWidget(this, {});
            this.error_popup.appendTo(this.$el);

            this.error_barcode_popup = new module.ErrorBarcodePopupWidget(this, {});
            this.error_barcode_popup.appendTo(this.$el);

            this.error_traceback_popup = new module.ErrorTracebackPopupWidget(this,{});
            this.error_traceback_popup.appendTo(this.$el);

            this.confirm_popup = new module.ConfirmPopupWidget(this,{});
            this.confirm_popup.appendTo(this.$el);

            this.unsent_orders_popup = new module.UnsentOrdersPopupWidget(this,{});
            this.unsent_orders_popup.appendTo(this.$el);

            // --------  Misc ---------

            this.close_button = new module.HeaderButtonWidget(this,{
                label: _t('Close'),
                action: function(){ 
                    var self = this;
                    if (!this.confirmed) {
                        this.$el.addClass('confirm');
                        this.$el.text(_t('Confirm'));
                        this.confirmed = setTimeout(function(){
                            self.$el.removeClass('confirm');
                            self.$el.text(_t('Close'));
                            self.confirmed = false;
                        },2000);
                    } else {
                        clearTimeout(this.confirmed);
                        this.pos_widget.close();
                    }
                },
            });
            this.close_button.appendTo(this.$('.pos-rightheader'));

            this.notification = new module.SynchNotificationWidget(this,{});
            this.notification.appendTo(this.$('.pos-rightheader'));

            if(this.pos.config.use_proxy){
                this.proxy_status = new module.ProxyStatusWidget(this,{});
                this.proxy_status.appendTo(this.$('.pos-rightheader'));
            }

            this.username   = new module.UsernameWidget(this,{});
            this.username.replace(this.$('.placeholder-UsernameWidget'));

            this.action_bar = new module.ActionBarWidget(this);
            this.action_bar.replace(this.$(".placeholder-ActionBarWidget"));

            this.paypad = new module.PaypadWidget(this, {});
            this.paypad.replace(this.$('.placeholder-PaypadWidget'));

            this.numpad = new module.NumpadWidget(this);
            this.numpad.replace(this.$('.placeholder-NumpadWidget'));

            this.order_widget = new module.OrderWidget(this, {});
            this.order_widget.replace(this.$('.placeholder-OrderWidget'));

            this.onscreen_keyboard = new module.OnscreenKeyboardWidget(this, {
                'keyboard_model': 'simple'
            });
            this.onscreen_keyboard.replace(this.$('.placeholder-OnscreenKeyboardWidget'));
            this.user_widget = new module.UserWidget(this,{});
            this.user_widget.replace(this.$('.placeholder-UserWidget'));

            // --------  Screen Selector ---------

            this.screen_selector = new module.ScreenSelector({
                pos: this.pos,
                screen_set:{
                    'products': this.product_screen,
                    'payment' : this.payment_screen,
                    'scale':    this.scale_screen,
                    'receipt' : this.receipt_screen,
                    'clientlist': this.clientlist_screen,
                    'invoice': this.invoice_screen,
                    'client': this.client_screen,
                },
                popup_set:{
                    'error': this.error_popup,
                    'error-barcode': this.error_barcode_popup,
                    'error-traceback': this.error_traceback_popup,
                    'confirm': this.confirm_popup,
                    'unsent-orders': this.unsent_orders_popup,
                },
                default_screen: 'products',
                default_mode: 'cashier',
            });

            if(this.pos.debug){
                this.debug_widget = new module.DebugWidget(this);
                this.debug_widget.appendTo(this.$('.pos-content'));
            }

            this.disable_rubberbanding();

        },

        changed_pending_operations: function () {
            var self = this;
            this.synch_notification.on_change_nbr_pending(self.pos.get('nbr_pending_operations').length);
        },
        // shows or hide the numpad and related controls like the paypad.
        set_numpad_visible: function(visible){
            if(visible !== this.numpad_visible){
                this.numpad_visible = visible;
                if(visible){
                    this.numpad.show();
                    this.paypad.show();
                }else{
                    this.numpad.hide();
                    this.paypad.hide();
                }
            }
        },
        //shows or hide the leftpane (contains the list of orderlines, the numpad, the paypad, etc.)
        set_leftpane_visible: function(visible){
            if(visible !== this.leftpane_visible){
                this.leftpane_visible = visible;
                if(visible){
                    this.$('.rightpane').removeClass('oe_hidden');
                    //this.$('.leftpane').css({'left':this.leftpane_width});
                }else{
                    this.$('.rightpane').addClass('oe_hidden');
                    //this.$('.leftpane').css({'left':'0px'});
                }
            }
        },
        close: function() {
            var self = this;

            function close(){
                self.pos.push_order().then(function(){
                    return new instance.web.Model("ir.model.data").get_func("search_read")([['name', '=', 'action_client_pos_menu']], ['res_id']).pipe(function(res) {
                        window.location = '/web#action=' + res[0]['res_id'];
                    },function(err,event) {
                        event.preventDefault();
                        self.screen_selector.show_popup('error',{
                            'message': _t('Could not close the point of sale.'),
                            'comment': _t('Your internet connection is probably down.'),
                        });
                        self.close_button.renderElement();
                    });
                });
            }

            var draft_order = _.find( self.pos.get('orders').models, function(order){
                return order.get('orderLines').length !== 0 && order.get('paymentLines').length === 0;
            });
            if(draft_order){
                if (confirm(_t("Pending orders will be lost.\nAre you sure you want to leave this session?"))) {
                    close();
                }
            }else{
                close();
            }
        },
        destroy: function() {
            this.pos.destroy();
            instance.webclient.set_content_full_screen(false);
            this._super();
        }
    });
}
