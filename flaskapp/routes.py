import os
import secrets
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, abort
from flaskapp import app, db, bcrypt, socketio
from flaskapp.models import User, ServiceProvider, Service, Order, NotificationStatus, OrderStatus, Complaint, Category, Notification
from flaskapp.forms import RegistrationForm, LoginForm, UpdateAccountForm, ReviewForm, ComplaintForm
from flask_login import login_user, current_user, logout_user, login_required
from sqlalchemy import or_
from datetime import datetime
from sqlalchemy.orm import joinedload
from functools import wraps
from flask_socketio import emit, join_room, leave_room
from flaskapp.models import create_dummy_data
from flask_bcrypt import Bcrypt
from random import uniform

bcrypt = Bcrypt()

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn

def getservices():
    categories = Category.query.all()
    obj = {}
    for category in categories:
        top_service = (
            db.session.query(Service).join(ServiceProvider).filter(Service.category_id == category.id, ServiceProvider.verified == True).order_by(Service.ratings.desc()).first()
        )
        if top_service:
            obj[category.name] = { 
                "id": top_service.id,
                "title": top_service.title,
                "description": top_service.description,
                "ser_price": top_service.ser_price,  # Updated key
                "ratings": top_service.ratings,
                "duration": top_service.duration,
            }
    return obj

def get_top_services_by_category():
    categories = Category.query.all()
    services_by_category = {}
    category_order_counts = {}

    for category in categories:
        top_services = (
            db.session.query(Service, db.func.count(Order.id).label('order_count'))
            .select_from(Service)
            .join(ServiceProvider, Service.provider_id == ServiceProvider.id)
            .outerjoin(Order, Order.ser_id == Service.id)
            .filter(Service.category_id == category.id, ServiceProvider.verified == True)
            .group_by(Service.id)
            .order_by(db.func.count(Order.id).desc())
            .limit(3)
            .all()
        )
        if top_services:
            services_by_category[category.name] = [service for service, order_count in top_services]
            category_order_counts[category.name] = sum(order_count for service, order_count in top_services)

    # Sort categories by the number of orders
    sorted_categories = sorted(category_order_counts.items(), key=lambda item: item[1], reverse=True)
    sorted_services_by_category = {category: services_by_category[category] for category, _ in sorted_categories}

    return sorted_services_by_category

@app.route("/")
@app.route("/home")
def home():
    services_by_category = get_top_services_by_category()
    return render_template('home.html', services_by_category=services_by_category)

@app.route("/about")
def about():
    return render_template('about.html', title='About')

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account', image_file=image_file, form=form)

@app.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    users = User.query.all()
    services = Service.query.all()
    unresolved_complaints = Complaint.query.filter_by(resolved=False).all()
    resolved_complaints = Complaint.query.filter_by(resolved=True).all()
    categories = Category.query.all()
    unverified_providers = ServiceProvider.query.filter_by(verified=False).all()
    return render_template('admin.html', users=users, services=services, unresolved_complaints=unresolved_complaints, resolved_complaints=resolved_complaints, categories=categories, unverified_providers=unverified_providers)

@app.route("/approve_provider/<int:provider_id>", methods=['POST'])
@login_required
@admin_required
def approve_provider(provider_id):
    provider = ServiceProvider.query.get_or_404(provider_id)
    provider.verified = True
    db.session.commit()
    flash('Service provider approved successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route("/reject_provider/<int:provider_id>", methods=['POST'])
@login_required
@admin_required
def reject_provider(provider_id):
    provider = ServiceProvider.query.get_or_404(provider_id)
    db.session.delete(provider)
    db.session.commit()
    flash('Service provider rejected and deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route("/add_category", methods=['POST'])
@login_required
@admin_required
def add_category():
    category_name = request.form.get('category_name')
    if category_name:
        new_category = Category(name=category_name)
        db.session.add(new_category)
        db.session.commit()
        flash('Category added successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route("/delete_category/<int:category_id>", methods=['POST'])
@login_required
@admin_required
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    db.session.delete(category)
    db.session.commit()
    flash('Category deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route("/complaint/<int:complaint_id>")
@login_required
@admin_required
def view_complaint(complaint_id):
    complaint = Complaint.query.get_or_404(complaint_id)
    order = Order.query.options(joinedload(Order.service)).get_or_404(complaint.order_id)
    return render_template('complaint_details.html', complaint=complaint, order=order)

@app.route("/complaint/<int:complaint_id>/refund", methods=['POST'])
@login_required
@admin_required
def refund_user(complaint_id):
    complaint = Complaint.query.get_or_404(complaint_id)
    complaint.resolved = True
    complaint.action_taken = "User refunded"
    db.session.commit()

    # Create notification for the user
    notification = Notification(
        user_id=complaint.user_id,
        message=f"Your complaint (ID: {complaint.id}) has been resolved with a refund.",
        date_posted=datetime.utcnow()
    )
    db.session.add(notification)
    db.session.commit()

    flash('User has been refunded.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route("/complaint/<int:complaint_id>/remove_provider", methods=['POST'])
@login_required
@admin_required
def remove_service_provider(complaint_id):
    complaint = Complaint.query.get_or_404(complaint_id)
    order = Order.query.get_or_404(complaint.order_id)
    service_provider = ServiceProvider.query.get_or_404(order.service_provider_id)
    db.session.delete(service_provider)
    complaint.resolved = True
    complaint.action_taken = "Service provider removed"
    db.session.commit()
    flash('Service provider has been removed.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route("/complaint/<int:complaint_id>/warn_provider", methods=['POST'])
@login_required
@admin_required
def warn_service_provider(complaint_id):
    complaint = Complaint.query.get_or_404(complaint_id)
    order = Order.query.get_or_404(complaint.order_id)
    service_provider = ServiceProvider.query.get_or_404(order.service_provider_id)
    complaint.resolved = True
    complaint.action_taken = "Service provider warned"
    db.session.commit()

    # Create notification for the service provider
    notification = Notification(
        user_id=service_provider.id,
        message=f"You have been warned regarding complaint (ID: {complaint.id}).",
        date_posted=datetime.utcnow()
    )
    db.session.add(notification)
    db.session.commit()

    flash('Service provider has been warned.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route("/service/<int:service_id>")
def servicedetails(service_id):
    details = Service.query.get_or_404(service_id)
    orders = Order.query.filter_by(ser_id=service_id).all()
    if orders:
        valid_ratings = [order.rate for order in orders if order.rate is not None]
        avg_rating = sum(valid_ratings) / len(valid_ratings) if valid_ratings else None
    else:
        avg_rating = None
    referrer = request.referrer  # Get the referrer URL
    return render_template('service_details.html', details=details, avg_rating=avg_rating, referrer=referrer)

@app.route('/join')
@login_required
def join():
    service_provider = ServiceProvider.query.filter_by(id=current_user.id).first()
    if service_provider:
        flash('Service providers cannot join as users.', 'danger')
        return redirect(url_for('home'))
    return redirect(url_for('containform'))

@app.route("/containform")
def containform():
    categories = Category.query.all()
    return render_template("createServiceProviderprofileform.html", categories=categories)

@app.route('/become_service_provider', methods=['GET', 'POST'])
@login_required
def become_service_provider():
    if request.method == 'POST':
        nid = request.form.get('nid')
        bio = request.form.get('bio')
        title = request.form.get('title')
        description = request.form.get('description')
        ser_price = request.form.get('ser_price')
        category_id = request.form.get('category')
        duration = request.form.get('duration')

        if not nid or not bio or not title or not description or not ser_price or not category_id:
            flash('All fields are required.', 'danger')
            return redirect(url_for('become_service_provider'))

        service_provider = db.session.query(ServiceProvider).filter(ServiceProvider.id == current_user.id).first()
        if service_provider is None:
            latitude = uniform(20.0, 26.0)
            longitude = uniform(88.0, 92.0)
            service_provider = ServiceProvider(id=current_user.id, nid=nid, bio=bio, latitude=latitude, longitude=longitude)
            db.session.add(service_provider)
            db.session.commit()

        service = Service(
            title=title,
            description=description,
            ser_price=ser_price,
            user_id=current_user.id,
            provider_id=current_user.id,
            ratings=1,
            category_id=category_id,
            duration=duration,
        )
        db.session.add(service)
        db.session.commit()

        flash('You are now a service provider! Please wait for admin approval.', 'success')
        return redirect(url_for('home'))

@app.route('/search_result', methods=['GET'])
def search_result():
    query = request.args.get('query', '').split()
    min_price = request.args.get('min_price', type=float)  
    max_price = request.args.get('max_price', type=float)  
    rating = request.args.get('rating', type=int) or 0   

    results = Service.query.join(ServiceProvider).filter(ServiceProvider.verified == True)  # Only show verified providers

    if query:
        filters = [Service.title.ilike(f"%{word}%") for word in query]
        results = results.filter(or_(*filters))

    if min_price is not None:
        results = results.filter(Service.ser_price >= min_price)

    if max_price is not None:
        results = results.filter(Service.ser_price <= max_price)

    if rating >= 0 and rating <=5:
        results = results.filter(Service.ratings >= rating)

    # Apply sorting after all filters
    results = results.order_by(Service.ser_price.asc(), Service.ratings.desc()).all()

    return render_template('search_results.html', result=results)

@app.route('/alluserorders')
@login_required
def alluserorders():
    orders = (
        db.session.query(Order, Service)
        .join(Service, Order.ser_id == Service.id)  
        .filter(Order.customer_id == current_user.id)  
        .all()  
    )

    combined_details = [
        {
            'id': order.id,
            'price': order.price,
            'order_datetime': order.order_datetime,
            'status': order.status,
            'service_title': service.title,
        }
        for order, service in orders
    ]

    return render_template('alluserorders.html', orders=combined_details)

@app.route('/userorderdetails/<int:order_id>')
@login_required
def userorderdetails(order_id):
    orders = (
        db.session.query(Order, Service)
        .join(Service, Order.ser_id == Service.id)  
        .filter(Order.id == order_id).first()
    )
    if orders:
        order, service = orders  
        combined_details = {
            'id': order.id,
            'price': order.price,
            'order_datetime': order.order_datetime,
            'status': order.status,
            'service_title': service.title,
        }

    if not orders:
        flash('Order not found', 'danger')
        return redirect(url_for('alluserorders'))

    return render_template('userorderdetails.html', details=combined_details)

@app.route('/placeorder/<int:service_id>')
@login_required
def placeorder(service_id):
    services = Service.query.filter_by(id=service_id).first()
    ref = request.referrer
    return render_template('orderform.html', details=services, referrer=ref)

@app.route('/submitOrder', methods=['POST'])
def postorder():
    if request.method == 'POST':
        location = request.form.get('location')
        date_time = datetime.fromisoformat(request.form.get('datetime'))
        price = request.form.get('price', type=float)
        service_id = request.form.get('service_id', type=int)
        service_provider_id = request.form.get('service_provider_id', type=int)

        if not location or not date_time or not price:
            flash("All fields are required!", "danger")
            return redirect('/submitOrder')

        # Generate random latitude and longitude for the order
        latitude = uniform(20.0, 26.0)
        longitude = uniform(88.0, 92.0)

        new_order = Order(
            order_loc=location,
            order_datetime=date_time,
            price=price,
            ser_id=service_id,
            service_provider_id=service_provider_id,
            customer_id=current_user.id,
            latitude=latitude,
            longitude=longitude
        )

        db.session.add(new_order)
        db.session.commit()
        flash("Order submitted successfully!", 'success')
        return redirect(url_for('payment', order_id=new_order.id))

@app.route('/notification')
def notification():
    checkprovider = ServiceProvider.query.filter_by(id = current_user.id).first()
    if checkprovider:
        note = (db.session.query(Order, Service).join(Service, Order.ser_id == Service.id).filter(Order.notifications == 'not_viewed', Order.service_provider_id == checkprovider.id).all())
        notes = [{
            'id': order.id,
            'price': order.price,
            'order_datetime': order.order_datetime,
            'status': order.status,
            'service_title': service.title,
            'loc' : order.order_loc,
        } for order, service in note]

        viewed = (db.session.query(Order, Service).join(Service, Order.ser_id == Service.id).filter(Order.notifications == 'viewed', Order.service_provider_id == checkprovider.id).all())
        views = [{
            'id': order.id,
            'price': order.price,
            'order_datetime': order.order_datetime,
            'status': order.status,
            'service_title': service.title,
            'loc' : order.order_loc,
        } for order, service in viewed]

        # Fetch warning notifications for service providers
        warning_notifications = Notification.query.filter(Notification.user_id == current_user.id, Notification.message.like('%warned%')).all()
    else:
        notes = None
        views = None
        warning_notifications = None

    # Fetch refund notifications for users
    refund_notifications = Notification.query.filter(Notification.user_id == current_user.id, Notification.message.like('%refunded%')).all()

    return render_template('notification.html', note = notes, viewed = views, refund_notifications=refund_notifications, warning_notifications=warning_notifications)

@app.route('/updateNotification/<int:order_id>')
def updateNotification(order_id):
    order = Order.query.filter_by(id=order_id).first()

    if order.notifications == NotificationStatus.not_viewed:
        order.notifications = NotificationStatus.viewed
        db.session.commit()
    else:
        order.notifications = NotificationStatus.not_viewed
        db.session.commit()

    return redirect(url_for('notification'))

@app.route('/acceptOrder/<int:order_id>', methods=['POST'])
def acceptOrder(order_id):
    order = Order.query.get_or_404(order_id)

    order.status = OrderStatus.accepted
    order.notifications = NotificationStatus.viewed
    db.session.commit()
    flash('Order status updated to "Accepted".', 'success')

    return redirect(url_for('notification'))

@app.route('/rejectOrder/<int:order_id>', methods=['POST'])
def rejectOrder(order_id):
    order = Order.query.get_or_404(order_id)

    order.status = OrderStatus.rejected
    order.notifications = NotificationStatus.viewed
    db.session.commit()
    flash('Order status updated to "Rejected".', 'success')

    return redirect(url_for('notification'))

@app.route("/accepted_orders", methods=['GET', 'POST'], endpoint='accepted_orders')
@login_required
def view_orders():
    service_provider = ServiceProvider.query.filter_by(id=current_user.id).first()
    if not service_provider:
        return "Access Denied: Not a Service Provider", 403

    # Query for accepted and ongoing orders with related service and customer information
    accepted_orders = db.session.query(Order, Service, User).join(
        Service, Order.ser_id == Service.id
    ).join(
        User, Order.customer_id == User.id
    ).filter(
        Order.service_provider_id == service_provider.id,
        Order.status.in_([OrderStatus.accepted, OrderStatus.on_the_way, OrderStatus.reached])
    ).all()

    # Query for completed orders with related service and customer information
    completed_orders = db.session.query(Order, Service, User).join(
        Service, Order.ser_id == Service.id
    ).join(
        User, Order.customer_id == User.id
    ).filter(
        Order.service_provider_id == service_provider.id,
        Order.status == OrderStatus.completed
    ).all()

    return render_template(
        'acceptedorders.html',
        accepted_orders=accepted_orders,
        completed_orders=completed_orders
    )

@app.route('/mark_reached/<int:order_id>', methods=['POST'])
@login_required
def mark_reached(order_id):
    order = Order.query.get_or_404(order_id)

    if order.status == 'reached':
        flash('This order is already marked as "Reached".', 'warning')
    else:
        order.status = OrderStatus.reached
        db.session.commit()
        flash('Order status updated to "Reached".', 'success')

    return redirect(url_for('accepted_orders'))

@app.route('/mark_ontheway/<int:order_id>', methods=['POST'])
@login_required
def mark_ontheway(order_id):  
    order = Order.query.get_or_404(order_id)

    order.status = OrderStatus.on_the_way 
    db.session.commit()
    flash('Order status updated to "On the way".', 'success')
    return redirect(url_for('accepted_orders'))

@app.route('/mark_completed/<int:order_id>', methods=['POST'])
@login_required
def mark_completed(order_id):
    order = Order.query.get_or_404(order_id)

    order.status = OrderStatus.completed
    db.session.commit()
    flash('Order status updated to "Completed".', 'success')
    return redirect(url_for('accepted_orders'))

@app.route('/chat')
@login_required
def chat():
    return render_template('chat.html', title='Chat')

# Handle a user joining a chat room
@socketio.on('join')
def on_join(data):
    room = data['room']
    username = current_user.username
    join_room(room)
    emit('message', {'msg': f'{username} has joined the room.'}, room=room)

# Handle a user leaving a chat room
@socketio.on('leave')
def on_leave(data):
    room = data['room']
    username = current_user.username
    leave_room(room)
    emit('message', {'msg': f'{username} has left the room.'}, room=room)

# Handle messages sent by users
@socketio.on('send_message')
def handle_message(data):
    room = data['room']
    emit('message', {'username': current_user.username, 'msg': data['msg']}, room=room)

@app.route('/order/<int:order_id>')
def order_details(order_id):
    order = Order.query.get(order_id)
    service_provider = ServiceProvider.query.get(order.service_provider_id)

    # Initial coordinates
    sp_lat, sp_lon = service_provider.latitude, service_provider.longitude
    order_lat, order_lon = order.latitude, order.longitude

    return render_template(
        'ordersdetails.html',
        order=order,
        service_provider=service_provider,
        service=order.service,
        customer=order.customer,
        sp_lat=sp_lat,
        sp_lon=sp_lon,
        order_lat=order_lat,
        order_lon=order_lon
    )

@app.route("/service/<int:service_id>/view_reviews")
def view_reviews(service_id):
    orders = Order.query.filter_by(ser_id=service_id).all()

    reviews = [{"review": order.review, "rate": order.rate, "customer": User.query.get(order.customer_id).username}
               for order in orders if order.review]

    return render_template('view_reviews.html', reviews=reviews, service_id=service_id)

@app.route('/payment/<int:order_id>', methods=['GET', 'POST'])
@login_required
def payment(order_id):
    order = Order.query.get_or_404(order_id)
    if order.customer_id != current_user.id:
        flash("Unauthorized access to payment.", "danger")
        return redirect(url_for('alluserorders'))

    if request.method == 'POST':
        payment_method = request.form.get('payment_method')
        if not payment_method:
            flash("Please select a payment method.", "danger")
            return redirect(url_for('payment', order_id=order_id))

        if payment_method == "Cash":
            flash("Payment successful using Cash.", "success")
            return redirect(url_for('alluserorders'))
        elif payment_method == "Credit Card":
            return redirect(url_for('credit_card_payment', order_id=order_id))
        elif payment_method == "Mobile Payment":
            return redirect(url_for('mobile_payment', order_id=order_id))

    service = Service.query.get_or_404(order.ser_id)
    return render_template(
        'payment.html',
        details=service,
        order_id=order.id,
        location=order.order_loc,
        datetime=order.order_datetime,
        price=order.price
    )

@app.route('/payment/credit_card/<int:order_id>', methods=['GET', 'POST'])
@login_required
def credit_card_payment(order_id):
    order = Order.query.get_or_404(order_id)

    if order.customer_id != current_user.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('alluserorders'))

    if request.method == 'POST':
        flash("Payment successful using Credit Card.", "success")
        return redirect(url_for('alluserorders'))

    return render_template('credit_card_payment.html', order=order)

@app.route('/payment/mobile/<int:order_id>', methods=['GET', 'POST'])
@login_required
def mobile_payment(order_id):
    order = Order.query.get_or_404(order_id)

    if order.customer_id != current_user.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('alluserorders'))

    if request.method == 'POST':
        flash("Payment successful using Mobile Payment.", "success")
        return redirect(url_for('alluserorders'))

    return render_template('mobile_payment.html', order=order)

@app.route('/review_order/<int:order_id>', methods=['GET', 'POST'])
@login_required
def review_order(order_id):
    order = Order.query.get_or_404(order_id)
    if request.method == 'POST':
        rating = request.form.get('rating', type=float)
        review = request.form.get('review')
        if rating is not None and review:
            order.rate = rating
            order.review = review
            db.session.commit()
            flash('Review submitted successfully!', 'success')
            return redirect(url_for('alluserorders'))
        else:
            flash('Please provide both rating and review.', 'danger')
    return render_template('review_order.html', order=order)

@app.route('/analytics')
@login_required
def analytics():
    service_provider_id = current_user.id  

    total_orders = Order.query.filter_by(service_provider_id=service_provider_id).count()

    total_revenue = (
        db.session.query(db.func.sum(Order.price))
        .filter_by(service_provider_id=service_provider_id)
        .scalar()
        or 0.0
    )

    most_requested_service_id = (
        db.session.query(Order.ser_id, db.func.count(Order.ser_id))
        .filter_by(service_provider_id=service_provider_id)
        .group_by(Order.ser_id)
        .order_by(db.func.count(Order.ser_id).desc())
        .first()
    )

    most_requested_service = (
        Service.query.get(most_requested_service_id[0]).title
        if most_requested_service_id
        else "N/A"
    )

    # Additional analytics data
    total_customers = (
        db.session.query(db.func.count(db.distinct(Order.customer_id)))
        .filter_by(service_provider_id=service_provider_id)
        .scalar()
    )

    average_rating = (
        db.session.query(db.func.avg(Order.rate))
        .filter_by(service_provider_id=service_provider_id)
        .scalar()
        or 0.0
    )

    total_complaints = (
        db.session.query(db.func.count(Complaint.id))
        .join(Order, Complaint.order_id == Order.id)
        .filter(Order.service_provider_id == service_provider_id)
        .scalar()
    )

    analytics_data = {
        "total_orders": total_orders,
        "revenue": total_revenue,
        "most_requested_service": most_requested_service,
        "total_customers": total_customers,
        "average_rating": round(average_rating, 2),
        "total_complaints": total_complaints,
    }
    return render_template('analytics.html', data=analytics_data)

@app.route('/submit_complaint/<int:order_id>', methods=['POST'])
@login_required
def submit_complaint(order_id):
    order = Order.query.get_or_404(order_id)
    complaint_text = request.form.get('complaint')
    if complaint_text:
        complaint = Complaint(order_id=order.id, user_id=current_user.id, message=complaint_text)
        db.session.add(complaint)
        db.session.commit()
        flash('Your complaint has been submitted.', 'success')
    else:
        flash('Please provide a complaint message.', 'danger')
    return redirect(url_for('userorderdetails', order_id=order_id))

@app.route('/create_dummy_data')
def create_data():
    create_dummy_data()
    flash('Dummy data created successfully!', 'success')
    return redirect(url_for('home'))

@app.route("/make_admin/<int:user_id>", methods=['POST'])
@login_required
@admin_required
def make_admin(user_id):
    user = User.query.get_or_404(user_id)
    user.is_admin = True
    db.session.commit()
    flash('User has been made an admin.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route("/delete_user/<int:user_id>", methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('User has been deleted.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route("/delete_service/<int:service_id>", methods=['POST'])
@login_required
@admin_required
def delete_service(service_id):
    service = Service.query.get_or_404(service_id)
    db.session.delete(service)
    db.session.commit()
    flash('Service has been deleted.', 'success')
    return redirect(url_for('admin_dashboard'))
