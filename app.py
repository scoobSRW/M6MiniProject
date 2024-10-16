from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from password import my_password  # Ensure this file contains your MySQL password
from marshmallow import Schema, fields, validate, ValidationError

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://root:{my_password}@localhost/e_commerce_database'
db = SQLAlchemy(app)
ma = Marshmallow(app)

# Home route for the welcome page
@app.route('/')
def home():
    return '''
    <html>
        <body>
            <h1>Hello! Welcome to my Module 6 Mini Project.</h1>
        </body>
    </html>
    '''

# Schemas
class CustomerSchema(ma.Schema):
    name = fields.String(required=True)
    email = fields.String(required=True)
    phone = fields.String(required=True)

    class Meta:
        fields = ("name", "email", "phone", "id")

class ProductSchema(ma.Schema):
    name = fields.String(required=True, validate=validate.Length(min=1))
    price = fields.Float(required=True, validate=validate.Range(min=0))

    class Meta:
        fields = ("name", "price", "id")

class OrderSchema(ma.Schema):
    date = fields.Date(required=True)
    customer_id = fields.Integer(required=True)
    product_ids = fields.List(fields.Integer(), required=True)

    class Meta:
        fields = ("date", "customer_id", "product_ids", "id")

product_schema = ProductSchema()
products_schema = ProductSchema(many=True)

customer_schema = CustomerSchema()
customers_schema = CustomerSchema(many=True)

order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)

# Association table for the many-to-many relationship between Orders and Products
order_product = db.Table('Order_Product',
    db.Column('order_id', db.Integer, db.ForeignKey('Orders.id'), primary_key=True),
    db.Column('product_id', db.Integer, db.ForeignKey('Products.id'), primary_key=True)
)

# Models
class Customer(db.Model):
    __tablename__ = 'Customers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(320))
    phone = db.Column(db.String(15))
    orders = db.relationship('Order', backref='customer')

class Order(db.Model):
    __tablename__ = 'Orders'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('Customers.id'), nullable=False)
    products = db.relationship('Product', secondary=order_product, backref='orders')

class CustomerAccount(db.Model):
    __tablename__ = 'Customer_Accounts'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('Customers.id'))
    customer = db.relationship('Customer', backref='customer_account', uselist=False)

class Product(db.Model):
    __tablename__ = 'Products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False)

# Product CRUD Endpoints
@app.route('/products', methods=['POST'])
def add_product():
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400

    new_product = Product(name=product_data['name'], price=product_data['price'])
    db.session.add(new_product)
    db.session.commit()
    return jsonify({"message": "Product added successfully"}), 201

@app.route('/products', methods=['GET'])
def get_products():
    products = Product.query.all()
    return products_schema.jsonify(products)

@app.route('/products/<int:id>', methods=['PUT'])
def update_product(id):
    product = Product.query.get_or_404(id)
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400

    product.name = product_data['name']
    product.price = product_data['price']
    db.session.commit()
    return jsonify({"message": "Product updated successfully"}), 200

@app.route('/products/<int:id>', methods=['DELETE'])
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": "Product deleted successfully"}), 200

# Customer Account CRUD Endpoints
@app.route('/customer-accounts', methods=['POST'])
def add_customer_account():
    try:
        data = request.json

        if not all(field in data for field in ('username', 'password', 'customer_id')):
            return jsonify({"message": "Missing required fields"}), 400

        customer = Customer.query.get(data['customer_id'])
        if not customer:
            return jsonify({"message": "Invalid customer ID"}), 400

        if CustomerAccount.query.filter_by(username=data['username']).first():
            return jsonify({"message": "Username already exists"}), 400

        new_account = CustomerAccount(
            id=data['customer_id'],  # Set the account id to be the same as the customer_id
            username=data['username'],
            password=data['password'],  # Remember to hash the password in a production app
            customer_id=data['customer_id']
        )
        db.session.add(new_account)
        db.session.commit()
        return jsonify({"message": "Customer account created successfully"}), 201

    except ValidationError as err:
        return jsonify(err.messages), 400
    except Exception as e:
        return jsonify({"message": str(e)}), 500  # Catch any other errors

@app.route('/customer-accounts/<int:id>', methods=['GET'])
def get_customer_account(id):
    account = CustomerAccount.query.get_or_404(id)
    account_data = {
        "username": account.username,
        "customer_id": account.customer_id,
        "customer_name": account.customer.name
    }
    return jsonify(account_data), 200

@app.route('/customer-accounts/<int:id>', methods=['PUT'])
def update_customer_account(id):
    account = CustomerAccount.query.get_or_404(id)
    data = request.json
    account.username = data['username']
    account.password = data['password']  # Add secure hashing in production
    db.session.commit()
    return jsonify({"message": "Customer account updated successfully"}), 200

@app.route('/customer-accounts/<int:id>', methods=['DELETE'])
def delete_customer_account(id):
    account = CustomerAccount.query.get_or_404(id)
    db.session.delete(account)
    db.session.commit()
    return jsonify({"message": "Customer account deleted successfully"}), 200

# Customer CRUD Endpoints
@app.route('/customers', methods=['GET'])
def get_customers():
    customers = Customer.query.all()
    return customers_schema.jsonify(customers)

@app.route('/customers/<int:id>', methods=['GET'])
def get_customer_by_id(id):
    customer = Customer.query.get_or_404(id)
    return customer_schema.jsonify(customer)

@app.route('/customers', methods=['POST'])
def add_customer():
    try:
        customer_data = customer_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400

    new_customer = Customer(name=customer_data['name'], email=customer_data['email'], phone=customer_data['phone'])
    db.session.add(new_customer)
    db.session.commit()
    return jsonify({"message": "New customer added successfully"}), 201

@app.route('/customers/<int:id>', methods=['PUT'])
def update_customer(id):
    customer = Customer.query.get_or_404(id)
    try:
        customer_data = customer_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400

    customer.name = customer_data['name']
    customer.email = customer_data['email']
    customer.phone = customer_data['phone']
    db.session.commit()
    return jsonify({"message": "Customer updated successfully"}), 200

@app.route('/customers/<int:id>', methods=['DELETE'])
def delete_customer(id):
    customer = Customer.query.get_or_404(id)
    db.session.delete(customer)
    db.session.commit()
    return jsonify({"message": "Customer deleted successfully"}), 200

# Order CRUD Endpoints
@app.route('/orders', methods=['POST'])
def add_order():
    try:
        order_data = order_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400

    new_order = Order(date=order_data['date'], customer_id=order_data['customer_id'])
    product_ids = order_data['product_ids']
    products = Product.query.filter(Product.id.in_(product_ids)).all()

    if len(products) != len(product_ids):
        return jsonify({"message": "Some product IDs are invalid."}), 400

    new_order.products.extend(products)
    db.session.add(new_order)
    db.session.commit()
    return jsonify({"message": "Order created successfully"}), 201

@app.route('/orders', methods=['GET'])
def get_orders():
    orders = Order.query.all()
    return orders_schema.jsonify(orders)

@app.route('/orders/<int:id>', methods=['GET'])
def get_order_by_id(id):
    order = Order.query.get_or_404(id)
    return order_schema.jsonify(order)

@app.route('/orders/<int:id>', methods=['PUT'])
def update_order(id):
    order = Order.query.get_or_404(id)
    try:
        order_data = order_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400

    order.date = order_data['date']
    order.customer_id = order_data['customer_id']

    # Update the products
    product_ids = order_data['product_ids']
    products = Product.query.filter(Product.id.in_(product_ids)).all()

    if len(products) != len(product_ids):
        return jsonify({"message": "Some product IDs are invalid."}), 400

    order.products = products
    db.session.commit()
    return jsonify({"message": "Order updated successfully"}), 200

@app.route('/orders/<int:id>', methods=['DELETE'])
def delete_order(id):
    order = Order.query.get_or_404(id)
    db.session.delete(order)
    db.session.commit()
    return jsonify({"message": "Order deleted successfully"}), 200

# Run the application
if __name__ == '__main__':
    app.run(debug=True)
