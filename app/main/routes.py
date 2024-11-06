from datetime import datetime, timezone
from flask import render_template, flash, redirect, url_for, request, g, \
    current_app, abort, jsonify
from flask_login import current_user, login_required
from flask_babel import _, get_locale
import sqlalchemy as sa
from app import db
import os
from app.main.forms import EditProfileForm, EmptyForm, PostForm, DeletePostForm, \
    MessageForm, FeedbackForm
from app.models import User, Post, Message, Notification, Chat, Feedback
from app.main import bp
from werkzeug.utils import secure_filename

from PIL import Image

@bp.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()
    g.locale = str(get_locale())


@bp.route('/', methods=["GET", "POST"])
@bp.route('/index', methods=["GET", "POST"])
@login_required
def index():
    form = PostForm()
    delete_form = DeletePostForm()
    if form.validate_on_submit():
        post = Post(body=form.post.data, author = current_user)
        db.session.add(post)
        db.session.commit()
        flash(_("Your post is now live!"))
        return redirect(url_for("main.index"))
    page = request.args.get("page", 1, type=int)
    posts = db.paginate(current_user.following_posts(), page=page,
                        per_page=current_app.config["POSTS_PER_PAGE"], 
                        error_out=False)
    next_url = url_for("main.index", page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for("main.index", page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title=_('Home'), form=form, 
                           delete_form=delete_form, posts=posts.items, 
                           next_rel=next_url, prev_url=prev_url)



@bp.route("/explore")
@login_required
def explore():
    delete_form = DeletePostForm()
    page = request.args.get("page", 1, type=int)
    query = sa.select(Post).order_by(Post.timestamp.desc())
    posts = db.paginate(query, page=page,
                        per_page=current_app.config["POSTS_PER_PAGE"], 
                        error_out=False)
    next_url = url_for("main.explore", page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for("main.explore", page=posts.prev_num) \
        if posts.has_prev else None
    return render_template("index.html", title=_('Explore'), posts=posts.items,
                           next_url=next_url, delete_form=delete_form,
                           prev_url=prev_url)


@bp.route('/user/<username>')
@login_required
def user(username):
    delete_form = DeletePostForm()
    user = db.first_or_404(sa.select(User).where(User.username == username))
    page = request.args.get("page", 1, type=int)
    query = user.posts.select().order_by(Post.timestamp.desc())
    posts = db.paginate(query, page=page, 
                        per_page=current_app.config["POSTS_PER_PAGE"],
                        error_out=False)
    next_url = url_for("main.user", username=user.username, 
                       page=posts.next_num) if posts.has_next else None
    prev_url  =url_for("main.user", username=user.username, 
                       page=posts.prev_num) if posts.has_prev else None
    form = EmptyForm()
    return render_template('user.html', user=user, posts=posts.items, delete_form=delete_form,
                           next_url=next_url, prev_url=prev_url, form=form)


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        # Update user information
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        # Handle file upload
        if form.avatar.data:
            avatar = form.avatar.data
            filename = secure_filename(avatar.filename)
            avatar_path = os.path.join(current_app.root_path, 'static/avatars', filename)
            # Ensure the directory exists
            os.makedirs(os.path.dirname(avatar_path), exist_ok=True)
            # Save the original image
            avatar.save(avatar_path)
            # Resize the image to 256x256 for the profile page
            resize_image(avatar_path, (256, 256))
            current_user.avatar_filename = filename
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('main.edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title=_('Edit Profile'), 
                           form=form)


def resize_image(image_path, size):
    try:
        with Image.open(image_path) as img:
            img.thumbnail(size)
            img.save(image_path)
    except Exception as e:
        print(f"Error resizing image: {e}")


@bp.route("/follow/<username>", methods=["POST"])
@login_required
def follow(username):
    form  = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == username))
        if user is None:
            flash(_("User %(username)s not found.", username=username))
            return redirect(url_for("main.index"))
        if user == current_user:
            flash(_("You cannot Follow yourself!"))
            return redirect(url_for("main.user", username=username))
        current_user.follow(user)
        db.session.commit()
        flash(_('You are following %(username)s!', username=username))
        return redirect(url_for("main.user", username=username))
    else:
        return redirect(url_for("main.index"))
    

@bp.route('/unfollow/<username>', methods=["POST"])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == username))
        if user is None:
            flash(_('User %(username)s not found.', username=username))
            return redirect(url_for("main.index"))
        if user == current_user:
            flash(_("This action can't be performed."))
            return redirect(url_for("main.user", username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash(_("you are not following %(username)s.", username=username))
        return redirect(url_for("main.user", username=username))
    else:
        return redirect(url_for("main.index"))


@bp.route("/delete_post/<int:post_id>", methods=["POST"])
@login_required
def delete_post(post_id):
    post = db.session.get(Post, post_id)
    page = request.form.get("page", 1, type=int)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash("Your post has been delete.")
    return redirect(url_for("main.index", page=page))


@bp.route("/user/<username>/popup")
@login_required
def user_popup(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))
    form = EmptyForm()
    return render_template("user_popup.html", user=user, form=form)

@bp.route('/send_message/<recipient>', methods=['GET', 'POST'])
@login_required
def send_message(recipient):
    user = db.first_or_404(sa.select(User).where(User.username == recipient))
    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(author=current_user, recipient=user, body=form.message.data)
        db.session.add(msg)
        user.add_notification('unread_message_count', user.unread_message_count())
        db.session.commit()
        flash(_('Your message has been sent.'))
        return redirect(url_for('main.user', username=recipient))
    print(f"Sending message to: {recipient}, Form validated: {form.validate_on_submit()}")
    return render_template('send_message.html', title=_('Send Message'),
                           form=form, recipient=recipient)

@bp.route('/messages')
@login_required
def messages():
    current_user.last_message_read_time = datetime.now(timezone.utc)
    current_user.add_notification('unread_message_count', 0)
    db.session.commit()
    
    page = request.args.get('page', 1, type=int)
    
    # Query to get both received and sent messages
    query = db.session.query(Message).filter(
        (Message.recipient_id == current_user.id) | (Message.sender_id == current_user.id)
    ).order_by(Message.timestamp.desc())
    
    messages = db.paginate(query, page=page,
                           per_page=current_app.config['POSTS_PER_PAGE'],
                           error_out=False)
    
    next_url = url_for('main.messages', page=messages.next_num) if messages.has_next else None
    prev_url = url_for('main.messages', page=messages.prev_num) if messages.has_prev else None
    
    return render_template('messages.html', messages=messages.items,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/notifications')
@login_required
def notifications():
    since = request.args.get('since', 0.0, type=float)
    query = current_user.notifications.select().where(
        Notification.timestamp > since).order_by(Notification.timestamp.asc())
    notifications = db.session.scalars(query)
    return [{
        'name': n.name,
        'data': n.get_data(),
        'timestamp': n.timestamp
    } for n in notifications]

@bp.route('/user/<username>/followers')
@login_required
def followers(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))
    page = request.args.get('page', 1, type=int)
    query = user.followers.select().order_by(User.username.asc())
    followers = db.paginate(query, page=page, per_page=current_app.config['POSTS_PER_PAGE'], error_out=False)
    next_url = url_for('main.followers', username=user.username, page=followers.next_num) if followers.has_next else None
    prev_url = url_for('main.followers', username=user.username, page=followers.prev_num) if followers.has_prev else None
    return render_template('followers.html', user=user, followers=followers.items, next_url=next_url, prev_url=prev_url)


@bp.route('/user/<username>/following')
@login_required
def following(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))
    page = request.args.get('page', 1, type=int)
    query = user.following.select().order_by(User.username.asc())
    following = db.paginate(query, page=page, per_page=current_app.config['POSTS_PER_PAGE'], error_out=False)
    next_url = url_for('main.following', username=user.username, page=following.next_num) if following.has_next else None
    prev_url = url_for('main.following', username=user.username, page=following.prev_num) if following.has_prev else None
    return render_template('following.html', user=user, following=following.items, next_url=next_url, prev_url=prev_url)


@bp.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    form = FeedbackForm()  # Create an instance of your feedback form
    if form.validate_on_submit():
        content = form.content.data
        feedback = Feedback(user_id=current_user.id, content=content)
        db.session.add(feedback)
        db.session.commit()
        flash('Your feedback has been submitted.')
        return redirect(url_for('main.user', username=current_user.username))
    feedback_list = Feedback.query.all()
    return render_template('feedback.html', form=form, feedback_list=feedback_list)


@bp.route('/delete_all_feedback', methods=['POST'])
@login_required
def delete_all_feedback():
    Feedback.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash('All your feedback has been deleted.')
    return redirect(url_for('main.feedback'))


@bp.route('/chat/<username>', methods=['GET', 'POST'])
@login_required
def chat(username):
    user = db.session.execute(sa.select(User).where(User.username == username)).scalar_one_or_none()
    if user is None or user == current_user:
        flash('Invalid user')
        return redirect(url_for('main.messages'))

    # Check if a chat between these users already exists
    chat = db.session.query(Chat).filter(
        (Chat.user1_id == current_user.id) & (Chat.user2_id == user.id) |
        (Chat.user1_id == user.id) & (Chat.user2_id == current_user.id)
    ).first()

    # If no chat exists, create a new one
    if chat is None:
        chat = Chat(user1=current_user, user2=user)
        db.session.add(chat)
        db.session.commit()

    # Load messages for this chat
    page = request.args.get('page', 1, type=int)
    messages = chat.messages.order_by(Message.timestamp.desc()).paginate(page=page, per_page=10)

    # Message form submission handling
    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(sender_id=current_user.id, chat_id=chat.id, body=form.message.data)
        db.session.add(msg)
        db.session.commit()
        return redirect(url_for('main.chat', username=username))

    return render_template('chat.html', chat=chat, messages=messages.items, form=form, other_user=user)
