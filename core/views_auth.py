"""
Authentication Views for LOSTFOUND - Custom raw HTML form handling
NO forms.py - All validation handled manually in views
"""

import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from core.models import Profile


# ============== Validation Helpers ==============

def validate_username(username: str) -> tuple[bool, str]:
    """Validate username."""
    if not username:
        return False, "Username is required"
    if len(username) < 3:
        return False, "Username must be at least 3 characters long"
    if len(username) > 150:
        return False, "Username must be less than 150 characters"
    if not re.match(r'^[\w.@+-]+$', username):
        return False, "Username can only contain letters, numbers, and @/./+/-/_ characters"
    if User.objects.filter(username=username).exists():
        return False, "Username already exists"
    return True, ""


def validate_email(email: str) -> tuple[bool, str]:
    """Validate email address."""
    if not email:
        return False, "Email is required"
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return False, "Invalid email format"
    if User.objects.filter(email=email).exists():
        return False, "Email already registered"
    return True, ""


def validate_password(password: str) -> tuple[bool, str]:
    """Validate password strength."""
    if not password:
        return False, "Password is required"
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if len(password) > 128:
        return False, "Password is too long"
    if not re.search(r'[A-Za-z]', password):
        return False, "Password must contain at least one letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    return True, ""


def validate_first_name(first_name: str) -> tuple[bool, str]:
    """Validate first name."""
    if not first_name or not first_name.strip():
        return False, "First name is required"
    if len(first_name.strip()) > 150:
        return False, "First name is too long"
    return True, ""


def validate_last_name(last_name: str) -> tuple[bool, str]:
    """Validate last name."""
    if not last_name or not last_name.strip():
        return False, "Last name is required"
    if len(last_name.strip()) > 150:
        return False, "Last name is too long"
    return True, ""


def validate_phone(phone: str) -> tuple[bool, str]:
    """Validate phone number (optional field)."""
    if not phone or not phone.strip():
        return True, ""  # Phone is optional
    phone_clean = phone.strip()
    if len(phone_clean) < 7 or len(phone_clean) > 20:
        return False, "Phone number must be between 7 and 20 digits"
    if not re.match(r'^[\d\s\-\+\(\)]+$', phone_clean):
        return False, "Invalid phone number format"
    return True, ""


def validate_address(address: str) -> tuple[bool, str]:
    """Validate address (optional field)."""
    if not address or not address.strip():
        return True, ""  # Address is optional
    if len(address.strip()) > 500:
        return False, "Address is too long"
    return True, ""


def validate_city(city: str) -> tuple[bool, str]:
    """Validate city (optional field)."""
    if not city or not city.strip():
        return True, ""  # City is optional
    if len(city.strip()) > 100:
        return False, "City name is too long"
    return True, ""


def validate_state(state: str) -> tuple[bool, str]:
    """Validate state (optional field)."""
    if not state or not state.strip():
        return True, ""  # State is optional
    if len(state.strip()) > 100:
        return False, "State name is too long"
    return True, ""


def validate_zip_code(zip_code: str) -> tuple[bool, str]:
    """Validate zip code (optional field)."""
    if not zip_code or not zip_code.strip():
        return True, ""  # Zip code is optional
    if len(zip_code.strip()) > 20:
        return False, "Zip code is too long"
    return True, ""


def validate_country(country: str) -> tuple[bool, str]:
    """Validate country (optional field)."""
    if not country or not country.strip():
        return True, ""  # Country is optional
    if len(country.strip()) > 100:
        return False, "Country name is too long"
    return True, ""


# ============== View Functions ==============

def signup_view(request):
    """
    Handle user signup with raw HTML form.
    Creates User and automatically creates Profile.
    """
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    
    errors = {}
    form_data = {}
    
    if request.method == 'POST':
        # Extract form data
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        city = request.POST.get('city', '').strip()
        state = request.POST.get('state', '').strip()
        zip_code = request.POST.get('zip_code', '').strip()
        country = request.POST.get('country', '').strip()
        
        # Store form data for re-rendering
        form_data = {
            'username': username,
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'phone': phone,
            'address': address,
            'city': city,
            'state': state,
            'zip_code': zip_code,
            'country': country,
        }
        
        # Validate all fields
        valid, msg = validate_username(username)
        if not valid:
            errors['username'] = msg
        
        valid, msg = validate_email(email)
        if not valid:
            errors['email'] = msg
        
        valid, msg = validate_password(password1)
        if not valid:
            errors['password1'] = msg
        
        if password1 != password2:
            errors['password2'] = "Passwords do not match"
        
        valid, msg = validate_first_name(first_name)
        if not valid:
            errors['first_name'] = msg
        
        valid, msg = validate_last_name(last_name)
        if not valid:
            errors['last_name'] = msg
        
        valid, msg = validate_phone(phone)
        if not valid:
            errors['phone'] = msg
        
        valid, msg = validate_address(address)
        if not valid:
            errors['address'] = msg
        
        valid, msg = validate_city(city)
        if not valid:
            errors['city'] = msg
        
        valid, msg = validate_state(state)
        if not valid:
            errors['state'] = msg
        
        valid, msg = validate_zip_code(zip_code)
        if not valid:
            errors['zip_code'] = msg
        
        valid, msg = validate_country(country)
        if not valid:
            errors['country'] = msg
        
        # If no errors, create user
        if not errors:
            try:
                with transaction.atomic():
                    # Create User
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=password1,
                        first_name=first_name,
                        last_name=last_name
                    )
                    
                    # Create Profile automatically
                    Profile.objects.create(
                        user=user,
                        phone=phone,
                        address=address,
                        city=city,
                        state=state,
                        zip_code=zip_code,
                        country=country
                    )
                    
                    # Log the user in
                    login(request, user)
                    
                    messages.success(request, f"Welcome, {user.first_name}! Your account has been created successfully.")
                    return redirect('core:dashboard')
                    
            except Exception as e:
                errors['__all__'] = f"An error occurred during registration: {str(e)}"
    
    context = {
        'errors': errors,
        'form_data': form_data,
        'page_title': 'Sign Up'
    }
    return render(request, 'core/signup.html', context)


def login_view(request):
    """
    Handle user login with raw HTML form.
    """
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    
    errors = {}
    form_data = {}
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        remember_me = request.POST.get('remember_me') == 'on'
        
        # Store form data for re-rendering
        form_data = {
            'username': username,
            'remember_me': remember_me,
        }
        
        # Validate input
        if not username:
            errors['username'] = "Username is required"
        
        if not password:
            errors['password'] = "Password is required"
        
        # Authenticate user
        if not errors:
            user = authenticate(request, username=username, password=password)
            
            if user is None:
                errors['__all__'] = "Invalid username or password"
            else:
                # Login the user
                login(request, user)
                
                # Set session expiry based on remember_me
                if remember_me:
                    request.session.set_expiry(1209600)  # 2 weeks
                else:
                    request.session.set_expiry(0)  # Browser close
                
                messages.success(request, f"Welcome back, {user.first_name or user.username}!")
                return redirect('core:dashboard')
    
    context = {
        'errors': errors,
        'form_data': form_data,
        'page_title': 'Login'
    }
    return render(request, 'core/login.html', context)


@login_required
def logout_view(request):
    """
    Handle user logout.
    """
    user = request.user
    logout(request)
    messages.info(request, f"Goodbye, {user.first_name or user.username}! You have been logged out successfully.")
    return redirect('core:login')


@login_required
def profile_view(request):
    """
    View and edit user profile.
    """
    user = request.user
    profile = get_object_or_404(Profile, user=user)
    errors = {}
    form_data = {}
    
    if request.method == 'POST':
        action = request.POST.get('action', 'update_profile')
        
        if action == 'update_profile':
            # Update profile information
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            phone = request.POST.get('phone', '').strip()
            address = request.POST.get('address', '').strip()
            city = request.POST.get('city', '').strip()
            state = request.POST.get('state', '').strip()
            zip_code = request.POST.get('zip_code', '').strip()
            country = request.POST.get('country', '').strip()
            
            # Store form data for re-rendering
            form_data = {
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone,
                'address': address,
                'city': city,
                'state': state,
                'zip_code': zip_code,
                'country': country,
            }
            
            # Validate
            valid, msg = validate_first_name(first_name)
            if not valid:
                errors['first_name'] = msg
            
            valid, msg = validate_last_name(last_name)
            if not valid:
                errors['last_name'] = msg
            
            valid, msg = validate_phone(phone)
            if not valid:
                errors['phone'] = msg
            
            valid, msg = validate_address(address)
            if not valid:
                errors['address'] = msg
            
            valid, msg = validate_city(city)
            if not valid:
                errors['city'] = msg
            
            valid, msg = validate_state(state)
            if not valid:
                errors['state'] = msg
            
            valid, msg = validate_zip_code(zip_code)
            if not valid:
                errors['zip_code'] = msg
            
            valid, msg = validate_country(country)
            if not valid:
                errors['country'] = msg
            
            if not errors:
                try:
                    with transaction.atomic():
                        user.first_name = first_name
                        user.last_name = last_name
                        user.save()
                        
                        profile.phone = phone
                        profile.address = address
                        profile.city = city
                        profile.state = state
                        profile.zip_code = zip_code
                        profile.country = country
                        profile.save()
                        
                        messages.success(request, "Profile updated successfully!")
                        return redirect('core:profile')
                        
                except Exception as e:
                    errors['__all__'] = f"An error occurred: {str(e)}"
        
        elif action == 'change_password':
            current_password = request.POST.get('current_password', '')
            new_password1 = request.POST.get('new_password1', '')
            new_password2 = request.POST.get('new_password2', '')
            
            if not current_password:
                errors['current_password'] = "Current password is required"
            
            if not new_password1:
                errors['new_password1'] = "New password is required"
            
            if new_password1 != new_password2:
                errors['new_password2'] = "New passwords do not match"
            
            if not errors:
                if not user.check_password(current_password):
                    errors['current_password'] = "Current password is incorrect"
                else:
                    valid, msg = validate_password(new_password1)
                    if not valid:
                        errors['new_password1'] = msg
            
            if not errors:
                try:
                    user.set_password(new_password1)
                    user.save()
                    messages.success(request, "Password changed successfully! Please login again.")
                    return redirect('core:login')
                except Exception as e:
                    errors['__all__'] = f"An error occurred: {str(e)}"
    
    # Prepare form data for display
    form_data = {
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'username': user.username,
        'phone': profile.phone,
        'address': profile.address,
        'city': profile.city,
        'state': profile.state,
        'zip_code': profile.zip_code,
        'country': profile.country,
    }
    
    context = {
        'user': user,
        'profile': profile,
        'errors': errors,
        'form_data': form_data,
        'page_title': 'My Profile'
    }
    return render(request, 'core/profile.html', context)


@login_required
def dashboard_view(request):
    """
    User dashboard view.
    """
    user = request.user
    profile = get_object_or_404(Profile, user=user)
    
    context = {
        'user': user,
        'profile': profile,
        'page_title': 'Dashboard'
    }
    return render(request, 'core/dashboard.html', context)
