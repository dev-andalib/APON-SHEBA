from datetime import datetime
from flaskapp import db, login_manager
from flask_login import UserMixin
from enum import Enum
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    orders = db.relationship('Order', backref='customer', lazy=True)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    services = db.relationship('Service', backref='creator', lazy=True)

    @property
    def is_service_provider(self):
        return ServiceProvider.query.filter_by(id=self.id).first() is not None

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}')"

class ServiceProvider(db.Model):
    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    nid = db.Column(db.String(50), unique=True, nullable=False)
    bio = db.Column(db.Text, nullable=True)
    services = db.relationship('Service', backref='provider', lazy=True)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    verified = db.Column(db.Boolean, nullable=False, default=False)
    user = db.relationship('User', backref='service_provider', lazy=True)

    def __repr__(self):
        return f"ServiceProvider('{self.nid}', '{self.bio}', Verified: {self.verified})"

class ServiceProviderService(db.Model):
    __tablename__ = 'service_provider_service'
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), primary_key=True)
    service_provider_id = db.Column(db.Integer, db.ForeignKey('service_provider.id'), primary_key=True)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    services = db.relationship('Service', backref='category', lazy=True)

    def __repr__(self):
        return f"Category('{self.name}')"

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('service_provider.id'), nullable=False)
    ratings = db.Column(db.Integer, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    ser_price = db.Column(db.Float, nullable=False)
    orders = db.relationship('Order', backref='linked_service', lazy=True)

    def __repr__(self):
        return f'<Service {self.id}, Title: {self.title}, Category: {self.category.name}, Date: {self.date_posted}>'

    def set_ratings(self, value):
        if 0 <= value <= 5:
            self.ratings = value
        else:
            raise ValueError("Ratings must be between 0 and 5")

class OrderStatus(Enum):
    pending = 'pending'
    accepted = 'accepted'
    on_the_way = 'on the way'
    reached = 'reached'
    completed = 'completed'
    rejected = 'rejected'

class NotificationStatus(Enum):
    not_viewed = 'not viewed'
    viewed = 'viewed'

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_loc = db.Column(db.String(200), nullable=False)
    order_datetime = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.Enum(OrderStatus), nullable=False, default=OrderStatus.pending)
    review = db.Column(db.Text, nullable=True)
    rate = db.Column(db.Integer, nullable=True)
    price = db.Column(db.Float, nullable=False)
    notifications = db.Column(db.Enum(NotificationStatus), default=NotificationStatus.not_viewed)
    ser_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    service = db.relationship('Service', backref='service_orders', lazy=True)  # Renamed backref
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    service_provider_id = db.Column(db.Integer, db.ForeignKey('service_provider.id'), nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    def __repr__(self):
        return f'<Order {self.id}, Location: {self.order_loc}, Price: {self.price}, Status: {self.status.value}, Notifications: {self.notifications.value}>'

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    resolved = db.Column(db.Boolean, nullable=False, default=False)
    action_taken = db.Column(db.String(100), nullable=True)

    order = db.relationship('Order', backref='complaints', lazy=True)
    user = db.relationship('User', backref='complaints', lazy=True)

    def __repr__(self):
        return f"Complaint('{self.id}', '{self.date_posted}', '{self.message}')"

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship('User', backref='notifications', lazy=True)

    def __repr__(self):
        return f"Notification('{self.id}', '{self.message}', '{self.date_posted}')"























def create_dummy_data():
    from flaskapp import db
    from flaskapp.models import User, ServiceProvider, Service, Order, Category, Complaint, Notification
    from datetime import datetime
    import random

    # Bengali names for users
    bengali_names = [
        'Arjun', 'Amit', 'Bijoy', 'Chandan', 'Dipak', 'Esha', 'Farhan', 'Gopal', 'Harun', 'Ishita',
        'Jahid', 'Kabir', 'Liton', 'Mithun', 'Nadia', 'Omar', 'Puja', 'Quazi', 'Rana', 'Sima',
        'Tuhin', 'Usha', 'Vikram', 'Wahid', 'Xavier', 'Yasmin', 'Zahid', 'Anika', 'Bithi', 'Chitra',
        'Debashish', 'Elina', 'Fahim', 'Gita', 'Hassan', 'Indira', 'Joya', 'Kamal', 'Laila', 'Mona',
        'Nafisa', 'Oishi', 'Parvez', 'Quamrul', 'Rafiq', 'Shima', 'Tanvir', 'Uday', 'Vivek', 'Wasim'
    ]

    # Create dummy users
    users = []
    for i in range(1, 51):
        hashed_password = bcrypt.generate_password_hash('password').decode('utf-8')
        user = User(username=bengali_names[i-1], email=f'{bengali_names[i-1].lower()}@example.com', password=hashed_password, is_admin=(i == 1))
        users.append(user)
    db.session.add_all(users)
    db.session.commit()

    # Create dummy service providers
    service_providers = []
    for i in range(1, 51):
        sp = ServiceProvider(
            id=users[i-1].id, 
            nid=f'{random.randint(100000000, 999999999)}', 
            bio=f'Service Provider {bengali_names[i-1]} Bio', 
            verified=bool(random.getrandbits(1)), 
            latitude=random.uniform(20.0, 26.0), 
            longitude=random.uniform(88.0, 92.0)
        )
        service_providers.append(sp)
    db.session.add_all(service_providers)
    db.session.commit()

    # Actual names for categories
    category_names = ['Cleaning', 'Plumbing', 'Electrical', 'Carpentry', 'Painting']
    categories = [Category(name=name) for name in category_names]
    db.session.add_all(categories)
    db.session.commit()

    # Real service names matching categories
    service_names = {
        'Cleaning': ['House Cleaning', 'Office Cleaning', 'Window Cleaning', 'Carpet Cleaning', 'Deep Cleaning'],
        'Plumbing': ['Leak Repair', 'Drain Cleaning', 'Pipe Installation', 'Water Heater Repair', 'Toilet Repair'],
        'Electrical': ['Wiring Installation', 'Light Fixture Installation', 'Electrical Repair', 'Circuit Breaker Replacement', 'Outlet Installation'],
        'Carpentry': ['Furniture Assembly', 'Cabinet Installation', 'Deck Building', 'Door Installation', 'Trim Work'],
        'Painting': ['Interior Painting', 'Exterior Painting', 'Wallpaper Removal', 'Fence Painting', 'Deck Staining']
    }

    # Create dummy services
    services = []
    for i in range(1, 51):
        category = random.choice(categories)
        service = Service(
            title=random.choice(service_names[category.name]), 
            description=f'{category.name} service description', 
            user_id=users[i-1].id, 
            provider_id=service_providers[i-1].id, 
            ratings=random.randint(1, 5), 
            category_id=category.id, 
            duration=random.randint(1, 5), 
            ser_price=random.randint(10, 100)  # Ensure ser_price is an integer
        )
        services.append(service)
    db.session.add_all(services)
    db.session.commit()

    # Names of locations in Bangladesh
    bangladesh_locations = [
        'Dhaka', 'Chittagong', 'Khulna', 'Rajshahi', 'Sylhet', 'Barisal', 'Rangpur', 'Comilla', 'Narayanganj', 'Gazipur',
        'Mymensingh', 'Cox\'s Bazar', 'Jessore', 'Nawabganj', 'Bogra', 'Dinajpur', 'Pabna', 'Tangail', 'Kushtia', 'Faridpur',
        'Noakhali', 'Feni', 'Brahmanbaria', 'Patuakhali', 'Jamalpur', 'Netrakona', 'Sherpur', 'Sunamganj', 'Habiganj', 'Maulvibazar',
        'Lakshmipur', 'Chandpur', 'Kishoreganj', 'Manikganj', 'Munshiganj', 'Narsingdi', 'Shariatpur', 'Madaripur', 'Gopalganj', 'Jhalokathi',
        'Barguna', 'Bhola', 'Pirojpur', 'Bandarban', 'Khagrachari', 'Rangamati', 'Bagerhat', 'Satkhira', 'Magura', 'Meherpur'
    ]

    # Create dummy orders
    orders = []
    for i in range(1, 51):
        order = Order(
            order_loc=random.choice(bangladesh_locations), 
            order_datetime=datetime.utcnow(), 
            status=random.choice(list(OrderStatus)), 
            price=random.uniform(10.0, 100.0), 
            ser_id=services[i-1].id, 
            service_provider_id=service_providers[i-1].id, 
            customer_id=random.choice(users).id, 
            latitude=random.uniform(20.0, 26.0), 
            longitude=random.uniform(88.0, 92.0)
        )
        orders.append(order)
    db.session.add_all(orders)
    db.session.commit()

    # Create dummy complaints
    complaints = []
    for i in range(1, 51):
        complaint = Complaint(
            order_id=random.choice(orders).id, 
            user_id=random.choice(users).id, 
            message=f'Complaint {i} message', 
            date_posted=datetime.utcnow(), 
            resolved=bool(random.getrandbits(1))
        )
        complaints.append(complaint)
    db.session.add_all(complaints)
    db.session.commit()

    # Create dummy notifications
    notifications = []
    for i in range(1, 51):
        notification = Notification(
            user_id=random.choice(users).id, 
            message=f'Notification {i} message', 
            date_posted=datetime.utcnow()
        )
        notifications.append(notification)
    db.session.add_all(notifications)
    db.session.commit()

    print("Dummy data created successfully!")