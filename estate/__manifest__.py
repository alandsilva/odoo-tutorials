{
    'name': "Real Estate",
    'summary': "Manage real estate properties and offers",
    'version': '0.1',
    'category': 'Tutorials',
    'depends': ['base'],
    'data': [
        'security/ir.access.csv',
        'views/estate_property_offer_views.xml',
        'views/estate_property_views.xml',
        'views/estate_property_type_views.xml',
        'views/estate_property_tag_views.xml',
        'views/estate_menus.xml',
    ],
    'application': True,
    'installable': True,
    'author': "Alan Da Silva",
    'license': 'LGPL-3',
}
