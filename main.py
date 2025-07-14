from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from datetime import datetime
import os
import pandas as pd
import io
from flask_wtf import FlaskForm

from models import db, User, PrintRequest, SystemStatus
from forms import LoginForm, RegistrationForm, ProfileUpdateForm, PasswordChangeForm
from utils import setup_logging, init_limiter, login_limit
from config import config

# Initialize extensions
login_manager = LoginManager()
csrf = CSRFProtect()

def create_app(config_name='default'):
    app = Flask(__name__)
    
    # Load config
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    init_limiter(app)
    setup_logging(app)
    
    # Setup login manager
    login_manager.login_view = 'login'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Context processors
    @app.context_processor
    def utility_processor():
        return {
            'now': datetime.now(),
            'format_date': lambda date: date.strftime('%d-%m-%Y %H:%M') if date else ''
        }
        
    @app.context_processor
    def inject_system_status():
        status = SystemStatus.query.first()
        if not status:
            status = SystemStatus(is_active=True)
            db.session.add(status)
            db.session.commit()
        return dict(system_status=status)
        
    # Add cache headers for static files
    @app.after_request
    def add_header(response):
        if 'Cache-Control' not in response.headers:
            response.headers['Cache-Control'] = 'no-store'
        return response
        
    # Routes
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.is_admin():
                return redirect(url_for('admin_dashboard'))
            elif current_user.is_student():
                return redirect(url_for('student_dashboard'))
            elif current_user.is_faculty():
                return redirect(url_for('faculty_dashboard'))
        return redirect(url_for('login'))

    @app.route('/register', methods=['GET', 'POST'])
    @login_limit()
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
            
        form = RegistrationForm()
        if form.validate_on_submit():
            user = User(
                username=form.username.data,
                role='student',
                name=form.name.data,
                branch=form.branch.data,
                semester=form.semester.data
            )
            user.set_password(form.password.data)
            
            db.session.add(user)
            try:
                db.session.commit()
                app.logger.info(f'New user registered: {user.username}')
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                db.session.rollback()
                app.logger.error(f'Registration failed: {str(e)}')
                flash('Registration failed. Please try again.', 'error')
                
        return render_template('register.html', form=form)

    @app.route('/login', methods=['GET', 'POST'])
    @login_limit()
    def login():
        if current_user.is_authenticated:
            if current_user.is_admin():
                return redirect(url_for('admin_dashboard'))
            elif current_user.is_student():
                return redirect(url_for('student_dashboard'))
            elif current_user.is_faculty():
                return redirect(url_for('faculty_dashboard'))
            
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user and user.check_password(form.password.data):
                if user.is_admin():
                    return redirect(url_for('admin_login'))
                login_user(user)
                app.logger.info(f'User logged in: {user.username}')
                flash('Login successful!', 'success')
                if user.is_student():
                    return redirect(url_for('student_dashboard'))
                elif user.is_faculty():
                    return redirect(url_for('faculty_dashboard'))
                
            flash('Invalid username or password', 'error')
            app.logger.warning(f'Failed login attempt for username: {form.username.data}')
            
        return render_template('login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        username = current_user.username
        logout_user()
        app.logger.info(f'User logged out: {username}')
        return redirect(url_for('login'))

    @app.route('/student/dashboard')
    @login_required
    def student_dashboard():
        if not current_user.is_student():
            flash('Access denied.', 'error')
            return redirect(url_for('index'))
        
        # Check service status
        system_status = SystemStatus.query.first()
        service_active = system_status.is_active if system_status else True
        
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        user_requests = PrintRequest.query.filter_by(user_id=current_user.id)\
            .order_by(PrintRequest.created_at.desc())\
            .paginate(page=page, per_page=per_page)
            
        # Check if user has any pending request
        has_pending_request = PrintRequest.query.filter_by(
            user_id=current_user.id,
            status='pending'
        ).first() is not None

        # Get count of consecutive cancelled requests
        cancelled_count = 0
        recent_requests = PrintRequest.query.filter_by(user_id=current_user.id)\
            .order_by(PrintRequest.created_at.desc()).limit(3).all()
            
        for req in recent_requests:
            if req.status == 'cancelled':
                cancelled_count += 1
            else:
                break

        return render_template('student_dashboard.html',
                             requests=user_requests,
                             has_pending_request=has_pending_request,
                             cancelled_count=cancelled_count,
                             service_active=service_active)

    @app.route('/student/request-print', methods=['POST'])
    @login_required
    def request_print():
        if not current_user.is_student():
            flash('Access denied.', 'error')
            return redirect(url_for('index'))

        # Check if service is active
        system_status = SystemStatus.query.first()
        if system_status and not system_status.is_active:
            flash('Print service is currently unavailable.', 'error')
            return redirect(url_for('student_dashboard'))
        
        try:
            # Check for pending requests
            pending_request = PrintRequest.query.filter_by(
                user_id=current_user.id,
                status='pending'
            ).first()

            if pending_request:
                flash('You already have a pending request. Please wait for it to be processed.', 'error')
                return redirect(url_for('student_dashboard'))

            # Check for consecutive cancelled requests
            recent_requests = PrintRequest.query.filter_by(
                user_id=current_user.id
            ).order_by(PrintRequest.created_at.desc()).limit(3).all()
            
            cancelled_count = 0
            for req in recent_requests:
                if req.status == 'cancelled':
                    cancelled_count += 1
                else:
                    break

            if cancelled_count >= 3:
                flash('You have cancelled too many consecutive requests. Please wait for faculty assistance.', 'error')
                return redirect(url_for('student_dashboard'))

            # Create new request
            new_request = PrintRequest(user_id=current_user.id)
            db.session.add(new_request)
            db.session.commit()
            
            app.logger.info(f'New print request created by user: {current_user.username}')
            flash('Print request submitted successfully!', 'success')

        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Failed to create print request: {str(e)}')
            flash('Failed to submit print request. Please try again.', 'error')
            
        return redirect(url_for('student_dashboard'))

    @app.route('/student/cancel-request/<int:request_id>')
    @login_required
    def cancel_request(request_id):
        if not current_user.is_student():
            flash('Access denied.', 'error')
            return redirect(url_for('index'))

        try:
            print_request = PrintRequest.query.filter_by(
                id=request_id,
                user_id=current_user.id
            ).first_or_404()
            
            if print_request.status != 'pending':
                flash('Can only cancel pending requests!', 'error')
                return redirect(url_for('student_dashboard'))
            
            print_request.status = 'cancelled'
            db.session.commit()
            
            app.logger.info(f'Print request {request_id} cancelled by user: {current_user.username}')
            flash('Request cancelled successfully!', 'success')
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Failed to cancel print request: {str(e)}')
            flash('Failed to cancel request. Please try again.', 'error')
            
        return redirect(url_for('student_dashboard'))

    @app.route('/faculty/dashboard')
    @login_required
    def faculty_dashboard():
        if not current_user.is_faculty():
            flash('Access denied.', 'error')
            return redirect(url_for('index'))
            
        page = request.args.get('page', 1, type=int)
        per_page = 10
        search_username = request.args.get('username', '').strip()
        
        # Base query
        query = PrintRequest.query\
            .join(User)\
            .filter(PrintRequest.status == 'pending')
        
        # Add search filter if username provided
        if search_username:
            query = query.filter(User.username.ilike(f'%{search_username}%'))
        
        # Get pending requests with search filter
        pending_requests = query\
            .order_by(PrintRequest.created_at.desc())\
            .paginate(page=page, per_page=per_page)
            
        # Get system status
        system_status = SystemStatus.query.first()
        
        # Create form for CSRF protection
        form = FlaskForm()
        
        return render_template('faculty_dashboard.html', 
                             pending_requests=pending_requests,
                             search_username=search_username,
                             system_status=system_status,
                             form=form)

    @app.route('/faculty/mark-printed/<int:request_id>')
    @login_required
    def mark_printed(request_id):
        if not current_user.is_faculty():
            flash('Access denied.', 'error')
            return redirect(url_for('index'))

        print_request = PrintRequest.query.get_or_404(request_id)
        print_request.status = 'printed'
        
        try:
            db.session.commit()
            app.logger.info(f'Print request {request_id} marked as printed by faculty: {current_user.username}')
            flash('Request marked as printed!', 'success')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Failed to mark print request as printed: {str(e)}')
            flash('Failed to update request. Please try again.', 'error')
            
        return redirect(url_for('faculty_dashboard'))

    @app.route('/faculty/export-requests')
    @login_required
    def export_requests():
        if not current_user.is_faculty():
            flash('Access denied.', 'error')
            return redirect(url_for('index'))

        status = request.args.get('status', 'pending')
        if status not in ['pending', 'printed', 'cancelled']:
            flash('Invalid status specified.', 'error')
            return redirect(url_for('faculty_dashboard'))
        
        MAX_EXPORT_RECORDS = 1000
        
        requests = PrintRequest.query\
            .join(User)\
            .filter(PrintRequest.status == status)\
            .order_by(PrintRequest.created_at.desc())\
            .limit(MAX_EXPORT_RECORDS)\
            .all()
        
        if not requests:
            flash(f'No {status} requests found to export.', 'info')
            return redirect(url_for('faculty_dashboard'))
        
        # Mark as printed if pending
        if status == 'pending':
            try:
                for req in requests:
                    req.status = 'printed'
                    req.updated_at = datetime.utcnow()
                
                # Find all students with consecutive cancelled requests
                students_with_blocks = User.query.filter_by(role='student').all()
                unblocked_count = 0
                
                for student in students_with_blocks:
                    recent_requests = PrintRequest.query.filter_by(user_id=student.id)\
                        .order_by(PrintRequest.created_at.desc()).limit(3).all()
                    
                    cancelled_count = 0
                    for req in recent_requests:
                        if req.status == 'cancelled':
                            cancelled_count += 1
                        else:
                            break
                    
                    if cancelled_count >= 3:
                        unblocked_count += 1
                        # Reset the status of their recent cancelled requests
                        for req in recent_requests:
                            if req.status == 'cancelled':
                                req.status = 'expired'  # or any other status you prefer
                                req.updated_at = datetime.utcnow()
                
                db.session.commit()
                app.logger.info(f'{len(requests)} requests marked as printed and {unblocked_count} students unblocked by {current_user.username} during export')
                flash(f'{len(requests)} requests have been marked as printed and {unblocked_count} student blocks have been removed.', 'success')
                
            except Exception as e:
                db.session.rollback()
                app.logger.error(f'Failed to update request statuses during export: {str(e)}')
                flash('Failed to update request statuses. Please try again.', 'error')
                return redirect(url_for('faculty_dashboard'))

        # Group requests by branch and semester
        grouped_requests = {}
        for req in requests:
            key = (req.user.branch, req.user.semester)
            if key not in grouped_requests:
                grouped_requests[key] = []
            grouped_requests[key].append({
                'Date': req.created_at.strftime('%d-%m-%Y'),
                'Student Name': req.user.name,
                'Semester': req.user.semester,
                'Branch': req.user.branch,
                'Username': req.user.username
            })

        # Create Excel file with multiple sheets
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            workbook = writer.book
            
            # Create header format
            header_format = workbook.add_format({
                'bold': True,
                'font_size': 14,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#f0f0f0',
                'border': 1
            })
            
            # Create column header format
            column_format = workbook.add_format({
                'bold': True,
                'font_size': 11,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#e6e6e6',
                'border': 1
            })
            
            # Create data cell format
            cell_format = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'border': 1
            })

            # Create each sheet
            for (branch, semester), requests in grouped_requests.items():
                sheet_name = f"{semester} {branch}"
                df = pd.DataFrame(requests)
                
                # Write to sheet
                df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=2)
                worksheet = writer.sheets[sheet_name]
                
                # Write sheet header
                worksheet.merge_range('A1:E1', f"{branch} - {semester}", header_format)
                
                # Format column headers and data
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(2, col_num, value, column_format)
                    worksheet.set_column(col_num, col_num, 15, cell_format)
                
                # Auto-fit columns
                for col_num, value in enumerate(df.columns.values):
                    max_length = max(
                        df[value].astype(str).apply(len).max(),
                        len(value)
                    ) + 2
                    worksheet.set_column(col_num, col_num, max_length)

        # Generate filename
        filename = f'print_requests_{status}_{datetime.now().strftime("%Y%m%d")}.xlsx'
        
        return send_file(
            io.BytesIO(output.getvalue()),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    @app.route('/faculty/print-history')
    @login_required
    def print_history():
        if not current_user.is_faculty():
            flash('Access denied.', 'error')
            return redirect(url_for('index'))
            
        page = request.args.get('page', 1, type=int)
        per_page = 10
        search_username = request.args.get('username', '').strip()
        
        # Base query
        query = PrintRequest.query\
            .join(User)\
            .filter(PrintRequest.status == 'printed')
        
        # Add search filter if username provided
        if search_username:
            query = query.filter(User.username.ilike(f'%{search_username}%'))
        
        # Get printed requests history with search filter
        printed_requests = query\
            .order_by(PrintRequest.created_at.desc())\
            .paginate(page=page, per_page=per_page)
        
        return render_template('print_history.html', 
                             printed_requests=printed_requests,
                             search_username=search_username)

    @app.route('/student/settings', methods=['GET', 'POST'])
    @login_required
    def student_settings():
        if not current_user.is_student():
            flash('Access denied.', 'error')
            return redirect(url_for('index'))
        
        profile_form = ProfileUpdateForm(original_username=current_user.username, obj=current_user)
        password_form = PasswordChangeForm()
        
        if 'update_profile' in request.form and profile_form.validate_on_submit():
            current_user.username = profile_form.username.data
            current_user.name = profile_form.name.data
            current_user.branch = profile_form.branch.data
            current_user.semester = profile_form.semester.data
            
            try:
                db.session.commit()
                app.logger.info(f'Profile updated for user: {current_user.username}')
                flash('Profile updated successfully!', 'success')
            except Exception as e:
                db.session.rollback()
                app.logger.error(f'Profile update failed: {str(e)}')
                flash('Failed to update profile. Please try again.', 'error')
                
        elif 'change_password' in request.form and password_form.validate_on_submit():
            if current_user.check_password(password_form.current_password.data):
                current_user.set_password(password_form.new_password.data)
                try:
                    db.session.commit()
                    app.logger.info(f'Password changed for user: {current_user.username}')
                    flash('Password changed successfully!', 'success')
                except Exception as e:
                    db.session.rollback()
                    app.logger.error(f'Password change failed: {str(e)}')
                    flash('Failed to change password. Please try again.', 'error')
            else:
                flash('Current password is incorrect.', 'error')
            
        return render_template('student_settings.html', 
                             profile_form=profile_form, 
                             password_form=password_form)

    @app.route('/faculty/mark-cancelled/<int:request_id>')
    @login_required
    def mark_cancelled(request_id):
        if not current_user.is_faculty():
            flash('Access denied.', 'error')
            return redirect(url_for('index'))
        
        print_request = PrintRequest.query.get_or_404(request_id)
        
        if print_request.status != 'pending':
            flash('Can only cancel pending requests.', 'error')
            return redirect(url_for('faculty_dashboard'))
        
        print_request.status = 'cancelled'
        print_request.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            app.logger.info(f'Request #{request_id} marked as cancelled by {current_user.username}')
            flash('Request marked as cancelled.', 'success')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Failed to mark request #{request_id} as cancelled: {str(e)}')
            flash('Failed to cancel request. Please try again.', 'error')
        
        return redirect(url_for('faculty_dashboard'))

    @app.route('/faculty/toggle-service', methods=['POST'])
    @login_required
    def toggle_service():
        if not current_user.is_faculty():
            flash('Access denied.', 'error')
            return redirect(url_for('index'))
        
        password = request.form.get('password')
        reason = request.form.get('reason')
        
        if not current_user.check_password(password):
            flash('Invalid password. Action cancelled.', 'error')
            return redirect(url_for('faculty_dashboard'))
        
        try:
            # Get or create system status
            status = SystemStatus.query.first()
            if not status:
                status = SystemStatus(is_active=True)
                db.session.add(status)
            
            # Toggle status
            status.is_active = not status.is_active
            status.updated_at = datetime.utcnow()
            status.updated_by = current_user.id
            status.reason = reason
            
            db.session.commit()
            
            message = 'Print service activated.' if status.is_active else 'Print service terminated.'
            app.logger.info(f'Print service {"activated" if status.is_active else "terminated"} by {current_user.username}')
            flash(message, 'success')
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Failed to toggle service status: {str(e)}')
            flash('Failed to update service status. Please try again.', 'error')
        
        return redirect(url_for('faculty_dashboard'))

    @app.route('/auth/login', methods=['GET', 'POST'])
    def auth_login():
        # Clear any existing session
        logout_user()
        
        form = AuthLoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user and user.check_password(form.password.data) and user.is_auth():
                login_user(user)
                app.logger.info(f'Auth admin logged in: {user.username}')
                flash('Login successful!', 'success')
                return redirect(url_for('auth_students'))
            else:
                flash('Invalid credentials or insufficient permissions', 'error')
                app.logger.warning(f'Failed auth login attempt for username: {form.username.data}')
            
        return render_template('auth_login.html', form=form)

    @app.route('/auth/students')
    @login_required
    def auth_students():
        if not current_user.is_auth():
            logout_user()
            flash('Access denied. Only authentication administrators can access this page.', 'error')
            return redirect(url_for('auth_login'))
        
        # Get filter parameters
        page = request.args.get('page', 1, type=int)
        branch = request.args.get('branch', '')
        semester = request.args.get('semester', '')
        status = request.args.get('status', 'all')
        search = request.args.get('search', '').strip()
        
        # Base query for students
        query = User.query.filter_by(role='student')
        
        # Apply filters
        if branch:
            query = query.filter_by(branch=branch)
        if semester:
            query = query.filter_by(semester=semester)
        if status == 'verified':
            query = query.filter_by(is_verified=True)
        elif status == 'unverified':
            query = query.filter_by(is_verified=False)
        
        # Apply search if provided
        if search:
            query = query.filter(
                db.or_(
                    User.username.ilike(f'%{search}%'),
                    User.name.ilike(f'%{search}%')
                )
            )
        
        # Get paginated results
        students = query.order_by(User.created_at.desc()).paginate(
            page=page,
            per_page=10
        )
        
        # Get choices for dropdowns
        branch_choices = RegistrationForm.branch_choices
        semester_choices = RegistrationForm.semester_choices
        
        return render_template(
            'auth_students.html',
            students=students,
            branch_choices=branch_choices,
            semester_choices=semester_choices,
            branch=branch,
            semester=semester,
            status=status,
            search=search
        )

    @app.route('/auth/logout')
    @login_required
    def auth_logout():
        if current_user.is_auth():
            username = current_user.username
            logout_user()
            app.logger.info(f'Auth admin logged out: {username}')
            flash('Logged out successfully', 'success')
        return redirect(url_for('auth_login'))

    @app.route('/auth/export-students')
    @login_required
    def export_students():
        if not current_user.is_auth():
            return jsonify({'error': 'Access denied. Only authentication administrators can access this feature.'}), 403
        
        # Get filter parameters
        branch = request.args.get('branch', '')
        semester = request.args.get('semester', '')
        status = request.args.get('status', 'all')
        search = request.args.get('search', '').strip()
        export_format = request.args.get('format', 'xlsx')
        
        # Base query
        query = User.query.filter_by(role='student')
        
        # Apply filters
        if branch:
            query = query.filter_by(branch=branch)
        if semester:
            query = query.filter_by(semester=semester)
        if status == 'verified':
            query = query.filter_by(is_verified=True)
        elif status == 'unverified':
            query = query.filter_by(is_verified=False)
        
        # Apply search
        if search:
            query = query.filter(
                db.or_(
                    User.username.ilike(f'%{search}%'),
                    User.name.ilike(f'%{search}%')
                )
            )
        
        # Get all matching students
        students = query.all()
        
        # Create DataFrame
        data = []
        for student in students:
            data.append({
                'Username': student.username,
                'Name': student.name,
                'Branch': student.branch,
                'Semester': student.semester,
                'Registered On': student.created_at.strftime('%d-%m-%Y %H:%M'),
                'Status': 'Verified' if student.is_verified else 'Pending',
                'Verified On': student.verified_at.strftime('%d-%m-%Y %H:%M') if student.verified_at else '-',
                'Verified By': User.query.get(student.verified_by).username if student.verified_by else '-'
            })
        
        df = pd.DataFrame(data)
        
        # Create output buffer
        output = io.BytesIO()
        
        # Export based on format
        if export_format == 'xlsx':
            df.to_excel(output, index=False, engine='xlsxwriter')
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            extension = 'xlsx'
        else:
            df.to_csv(output, index=False)
            mimetype = 'text/csv'
            extension = 'csv'
        
        # Generate filename
        filename = f'students_export_{datetime.now().strftime("%Y%m%d_%H%M")}.{extension}'
        
        return send_file(
            io.BytesIO(output.getvalue()),
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )

    @app.route('/auth/verify-student/<int:student_id>', methods=['POST'])
    @login_required
    def verify_student(student_id):
        if not current_user.is_auth():
            return jsonify({'status': 'error', 'message': 'Access denied. Only authentication administrators can verify students.'}), 403
        
        student = User.query.get_or_404(student_id)
        if not student.is_student():
            return jsonify({'status': 'error', 'message': 'Invalid student ID'}), 400
        
        try:
            student.is_verified = True
            student.verified_at = datetime.utcnow()
            student.verified_by = current_user.id
            db.session.commit()
            
            app.logger.info(f'Student {student.username} verified by auth admin: {current_user.username}')
            return jsonify({
                'status': 'success',
                'message': f'Student {student.username} has been verified'
            })
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Error verifying student: {str(e)}')
            return jsonify({
                'status': 'error',
                'message': 'Failed to verify student'
            }), 500

    @app.route('/auth/delete-student/<int:student_id>', methods=['POST'])
    @login_required
    def delete_student(student_id):
        if not current_user.is_auth():
            return jsonify({'status': 'error', 'message': 'Access denied. Only authentication administrators can delete students.'}), 403

    @app.route('/admin/login', methods=['GET', 'POST'])
    def admin_login():
        if current_user.is_authenticated:
            if current_user.is_admin():
                return redirect(url_for('admin_dashboard'))
            logout_user()
            
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user and user.check_password(form.password.data) and user.is_admin():
                login_user(user)
                user.last_login = datetime.utcnow()
                db.session.commit()
                flash('Welcome to Admin Dashboard!', 'success')
                return redirect(url_for('admin_dashboard'))
            flash('Invalid credentials or insufficient permissions', 'error')
        return render_template('admin/login.html', form=form)

    @app.route('/admin/dashboard')
    @login_required
    def admin_dashboard():
        if not current_user.is_admin():
            logout_user()
            flash('Access denied. Admin only area.', 'error')
            return redirect(url_for('admin_login'))
        
        # Get filter parameters
        page = request.args.get('page', 1, type=int)
        branch = request.args.get('branch', '')
        semester = request.args.get('semester', '')
        role = request.args.get('role', '')
        status = request.args.get('status', '')
        search = request.args.get('search', '').strip()
        
        # Base query
        query = User.query
        
        # Apply filters
        if role and role != 'all':
            query = query.filter_by(role=role)
        if branch:
            query = query.filter_by(branch=branch)
        if semester:
            query = query.filter_by(semester=semester)
        if status == 'active':
            query = query.filter_by(is_active=True)
        elif status == 'inactive':
            query = query.filter_by(is_active=False)
        
        # Apply search
        if search:
            query = query.filter(
                db.or_(
                    User.username.ilike(f'%{search}%'),
                    User.name.ilike(f'%{search}%')
                )
            )
        
        # Get paginated results
        users = query.order_by(User.created_at.desc()).paginate(
            page=page,
            per_page=10
        )
        
        # Get system status
        system_status = SystemStatus.query.first()
        if not system_status:
            system_status = SystemStatus(is_active=True)
            db.session.add(system_status)
            db.session.commit()
        
        # Get statistics
        stats = {
            'total_users': User.query.count(),
            'total_students': User.query.filter_by(role='student').count(),
            'total_faculty': User.query.filter_by(role='faculty').count(),
            'active_users': User.query.filter_by(is_active=True).count(),
            'total_requests': PrintRequest.query.count(),
            'pending_requests': PrintRequest.query.filter_by(status='pending').count()
        }
        
        return render_template(
            'admin/dashboard.html',
            users=users,
            system_status=system_status,
            stats=stats,
            branch_choices=RegistrationForm.branch_choices,
            semester_choices=RegistrationForm.semester_choices,
            branch=branch,
            semester=semester,
            role=role,
            status=status,
            search=search
        )

    @app.route('/admin/toggle-user/<int:user_id>', methods=['POST'])
    @login_required
    def toggle_user(user_id):
        if not current_user.is_admin():
            return jsonify({'status': 'error', 'message': 'Access denied'}), 403
        
        user = User.query.get_or_404(user_id)
        
        # Don't allow deactivating admin accounts
        if user.is_admin():
            return jsonify({'status': 'error', 'message': 'Cannot modify admin accounts'}), 400
        
        try:
            user.is_active = not user.is_active
            db.session.commit()
            
            status = 'activated' if user.is_active else 'deactivated'
            app.logger.info(f'User {user.username} {status} by admin: {current_user.username}')
            
            return jsonify({
                'status': 'success',
                'message': f'User {user.username} has been {status}',
                'is_active': user.is_active
            })
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Failed to toggle user status: {str(e)}')
            return jsonify({'status': 'error', 'message': 'Failed to update user status'}), 500

    @app.route('/admin/delete-user/<int:user_id>', methods=['POST'])
    @login_required
    def delete_user(user_id):
        if not current_user.is_admin():
            return jsonify({'status': 'error', 'message': 'Access denied'}), 403
        
        user = User.query.get_or_404(user_id)
        
        # Don't allow deleting admin accounts
        if user.is_admin():
            return jsonify({'status': 'error', 'message': 'Cannot delete admin accounts'}), 400
        
        try:
            # Delete associated print requests first
            PrintRequest.query.filter_by(user_id=user_id).delete()
            
            # Delete the user
            db.session.delete(user)
            db.session.commit()
            
            app.logger.info(f'User {user.username} deleted by admin: {current_user.username}')
            return jsonify({
                'status': 'success',
                'message': f'User {user.username} has been deleted'
            })
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Failed to delete user: {str(e)}')
            return jsonify({'status': 'error', 'message': 'Failed to delete user'}), 500

    @app.route('/admin/toggle-service', methods=['POST'])
    @login_required
    def admin_toggle_service():
        if not current_user.is_admin():
            return jsonify({'status': 'error', 'message': 'Access denied'}), 403
        
        try:
            status = SystemStatus.query.first()
            if not status:
                status = SystemStatus(is_active=True)
                db.session.add(status)
            
            status.is_active = not status.is_active
            status.updated_at = datetime.utcnow()
            status.updated_by = current_user.id
            status.reason = request.form.get('reason')
            
            db.session.commit()
            
            new_status = 'activated' if status.is_active else 'terminated'
            app.logger.info(f'Print service {new_status} by admin: {current_user.username}')
            
            return jsonify({
                'status': 'success',
                'message': f'Print service has been {new_status}',
                'is_active': status.is_active
            })
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Failed to toggle service status: {str(e)}')
            return jsonify({'status': 'error', 'message': 'Failed to update service status'}), 500

    @app.route('/admin/export-users')
    @login_required
    def export_users():
        if not current_user.is_admin():
            return jsonify({'error': 'Access denied'}), 403
        
        try:
            users = User.query.all()
            data = []
            
            for user in users:
                if user.is_admin():  # Skip admin accounts in export
                    continue
                    
                data.append({
                    'Username': user.username,
                    'Role': user.role.title(),
                    'Name': user.name,
                    'Branch': user.branch,
                    'Semester': user.semester,
                    'Status': 'Active' if user.is_active else 'Inactive',
                    'Created On': user.created_at.strftime('%d-%m-%Y %H:%M'),
                    'Last Login': user.last_login.strftime('%d-%m-%Y %H:%M') if user.last_login else 'Never',
                    'Total Requests': PrintRequest.query.filter_by(user_id=user.id).count(),
                    'Pending Requests': PrintRequest.query.filter_by(user_id=user.id, status='pending').count()
                })
            
            df = pd.DataFrame(data)
            output = io.BytesIO()
            
            # Export as Excel
            df.to_excel(output, index=False, engine='xlsxwriter')
            output.seek(0)
            
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'users_export_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
            )
            
        except Exception as e:
            app.logger.error(f'Failed to export users: {str(e)}')
            return jsonify({'status': 'error', 'message': 'Failed to export users'}), 500

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        app.logger.error(f'Page not found: {request.url}')
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.error(f'Server Error: {error}')
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        app.logger.error(f'Forbidden access: {request.url}')
        return render_template('errors/403.html'), 403

    @app.errorhandler(401)
    def unauthorized_error(error):
        app.logger.error(f'Unauthorized access: {request.url}')
        return render_template('errors/401.html'), 401

    # Create tables and default users
    with app.app_context():
        db.create_all()
        
        # Create default admin account if it doesn't exist
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', role='admin', name='Administrator')
            admin.set_password('admin123')
            db.session.add(admin)
        
        # Create default faculty account if it doesn't exist
        faculty = User.query.filter_by(username='faculty1').first()
        if not faculty:
            faculty = User(username='faculty1', role='faculty', name='Faculty Member')
            faculty.set_password('adminpass')
            db.session.add(faculty)
            
        # Create initial system status if it doesn't exist
        status = SystemStatus.query.first()
        if not status:
            status = SystemStatus(is_active=True)
            db.session.add(status)
            
        db.session.commit()
        
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000)