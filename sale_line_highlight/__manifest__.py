{
    'name': 'Sale Line Highlight',
    'version': '18.0.1.0.0',
    'summary': 'Resalta líneas de pedido de venta según el producto',
    'description': 'Añade fondo verde a líneas de sale.order donde el producto sea product.template id=29',
    'author': 'Custom',
    'category': 'Sales',
    'depends': ['sale'],
    'data': [
        'views/sale_order_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sale_line_highlight/static/src/css/sale_line_highlight.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
