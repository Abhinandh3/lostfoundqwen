import os
import json
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone

from .models import (
    Profile, Case, CaseImage, SightingReport, DetectiveRequest,
    CaseAssignment, InvestigationUpdate, DetectiveAchievement, Feedback, Blog
)
from .ai_engine import extract_image_embedding, search_similar_images, get_model_status


def validate_case_data(post_data):
    """Manual validation for case creation data."""
    errors = []
    cleaned_data = {}
    
    title = post_data.get('title', '').strip()
    if not title:
        errors.append("Title is required.")
    elif len(title) < 5:
        errors.append("Title must be at least 5 characters.")
    cleaned_data['title'] = title
    
    description = post_data.get('description', '').strip()
    if not description:
        errors.append("Description is required.")
    cleaned_data['description'] = description
    
    case_type = post_data.get('case_type', '')
    valid_types = [choice[0] for choice in Case.CASE_TYPE_CHOICES]
    if case_type not in valid_types:
        errors.append("Invalid case type.")
    cleaned_data['case_type'] = case_type
    
    location = post_data.get('location', '').strip()
    if not location:
        errors.append("Location is required.")
    cleaned_data['location'] = location
    
    lat = post_data.get('latitude', '')
    lng = post_data.get('longitude', '')
    
    try:
        cleaned_data['latitude'] = float(lat) if lat else None
        cleaned_data['longitude'] = float(lng) if lng else None
    except (ValueError, TypeError):
        errors.append("Invalid coordinates format.")
    
    date_str = post_data.get('date_occurred', '')
    if date_str:
        try:
            cleaned_data['date_occurred'] = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            errors.append("Invalid date format. Use YYYY-MM-DD.")
    else:
        cleaned_data['date_occurred'] = None
    
    cleaned_data['status'] = post_data.get('status', 'OPEN')
    
    return cleaned_data, errors


@login_required
def create_case(request):
    """Handle case creation with multiple image uploads and AI embedding generation."""
    if request.method == 'POST':
        cleaned_data, errors = validate_case_data(request.POST)
        
        images = request.FILES.getlist('images')
        if not images:
            errors.append("At least one image is required.")
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'core/case_form.html', {
                'form_data': request.POST,
                'errors': errors
            })
        
        try:
            with transaction.atomic():
                case = Case.objects.create(
                    user=request.user,
                    title=cleaned_data['title'],
                    description=cleaned_data['description'],
                    case_type=cleaned_data['case_type'],
                    location=cleaned_data['location'],
                    latitude=cleaned_data['latitude'],
                    longitude=cleaned_data['longitude'],
                    date_occurred=cleaned_data['date_occurred'],
                    status=cleaned_data['status']
                )
                
                # Process each image and generate embeddings
                for img_file in images:
                    try:
                        case_image = CaseImage.objects.create(
                            case=case,
                            image=img_file
                        )
                        
                        # Generate and save CLIP embedding
                        embedding = extract_image_embedding(case_image.image.path)
                        if embedding:
                            case_image.clip_embedding = json.dumps(embedding)
                            case_image.save(update_fields=['clip_embedding'])
                            
                    except Exception as e:
                        messages.error(request, f"Failed to process image {img_file.name}: {str(e)}")
                        continue
                
                messages.success(request, f"Case '{case.title}' created successfully!")
                return redirect('case_detail', pk=case.pk)
                
        except Exception as e:
            messages.error(request, f"Database error: {str(e)}")
            return render(request, 'core/case_form.html', {
                'form_data': request.POST,
                'errors': [str(e)]
            })
    
    return render(request, 'core/case_form.html')


def case_list(request):
    """Display list of all cases with filtering options."""
    cases = Case.objects.select_related('user').prefetch_related('images').all()
    
    # Filtering
    case_type = request.GET.get('type')
    status = request.GET.get('status')
    search_query = request.GET.get('q', '')
    
    if case_type:
        cases = cases.filter(case_type=case_type)
    if status:
        cases = cases.filter(status=status)
    if search_query:
        cases = cases.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(location__icontains=search_query)
        )
    
    context = {
        'cases': cases,
        'case_types': Case.CASE_TYPE_CHOICES,
        'statuses': Case.STATUS_CHOICES,
        'filters': {
            'type': case_type,
            'status': status,
            'q': search_query
        }
    }
    return render(request, 'core/case_list.html', context)


def case_detail(request, pk):
    """Display case details with images and sighting reports."""
    case = get_object_or_404(
        Case.objects.select_related('user').prefetch_related('images', 'sighting_reports'),
        pk=pk
    )
    
    # Check if user has already submitted a sighting report for this case
    user_report = None
    if request.user.is_authenticated:
        user_report = SightingReport.objects.filter(case=case, reporter=request.user).first()
    
    context = {
        'case': case,
        'user_report': user_report,
        'is_assigned_detective': False
    }
    
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        if request.user.profile.is_detective:
            assignment = CaseAssignment.objects.filter(
                case=case,
                detective=request.user,
                status='ACTIVE'
            ).exists()
            context['is_assigned_detective'] = assignment
    
    return render(request, 'core/case_detail.html', context)


@login_required
def submit_sighting_report(request, case_pk):
    """Handle sighting report submission."""
    case = get_object_or_404(Case, pk=case_pk)
    
    if request.method == 'POST':
        description = request.POST.get('description', '').strip()
        sighting_date = request.POST.get('sighting_date', '')
        location = request.POST.get('location', '').strip()
        
        errors = []
        if not description:
            errors.append("Description is required.")
        if not location:
            errors.append("Location is required.")
        
        sighting_image = request.FILES.get('image')
        
        parsed_date = None
        if sighting_date:
            try:
                parsed_date = datetime.strptime(sighting_date, '%Y-%m-%d').date()
            except ValueError:
                errors.append("Invalid date format.")
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect('case_detail', pk=case_pk)
        
        try:
            report = SightingReport.objects.create(
                case=case,
                reporter=request.user,
                description=description,
                location=location,
                sighting_date=parsed_date,
                image=sighting_image if sighting_image else None
            )
            messages.success(request, "Sighting report submitted successfully!")
            
            # Update case status if needed
            if case.status == 'OPEN':
                case.status = 'UNDER_INVESTIGATION'
                case.save(update_fields=['status'])
                
        except Exception as e:
            messages.error(request, f"Error submitting report: {str(e)}")
        
        return redirect('case_detail', pk=case_pk)
    
    return redirect('case_detail', pk=case_pk)


@login_required
def ai_search(request):
    """AI-powered image similarity search using CLIP embeddings."""
    results = []
    model_status = get_model_status()
    
    if request.method == 'POST':
        query_image = request.FILES.get('query_image')
        
        if not query_image:
            messages.error(request, "No image uploaded.")
            return render(request, 'core/ai_search.html', {
                'results': [],
                'model_status': model_status
            })
        
        try:
            # Save temporary file path
            temp_path = os.path.join(settings.MEDIA_ROOT, 'temp', query_image.name)
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            
            with open(temp_path, 'wb+') as destination:
                for chunk in query_image.chunks():
                    destination.write(chunk)
            
            # Extract embedding from query image
            query_embedding = extract_image_embedding(temp_path)
            
            if not query_embedding:
                messages.error(request, "Failed to extract image embedding.")
                return render(request, 'core/ai_search.html', {
                    'results': [],
                    'model_status': model_status
                })
            
            # Search for similar images
            similar_images = search_similar_images(query_embedding, top_k=10)
            
            results = []
            for img_data in similar_images:
                case_image = CaseImage.objects.filter(pk=img_data['id']).first()
                if case_image:
                    results.append({
                        'case_image': case_image,
                        'similarity': round(img_data['similarity'] * 100, 2),
                        'case': case_image.case
                    })
            
            # Clean up temp file
            try:
                os.remove(temp_path)
            except:
                pass
                
        except Exception as e:
            messages.error(request, f"Search error: {str(e)}")
            results = []
    
    return render(request, 'core/ai_search.html', {
        'results': results,
        'model_status': model_status
    })


# Detective Workflow Views

@login_required
def request_detective(request, case_pk):
    """Allow users to request a detective for their case."""
    case = get_object_or_404(Case, pk=case_pk)
    
    if request.user != case.user:
        messages.error(request, "Only the case owner can request a detective.")
        return redirect('case_detail', pk=case_pk)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        
        if not reason:
            messages.error(request, "Reason for request is required.")
            return redirect('case_detail', pk=case_pk)
        
        try:
            DetectiveRequest.objects.create(
                case=case,
                requested_by=request.user,
                reason=reason,
                status='PENDING'
            )
            messages.success(request, "Detective request submitted successfully!")
            case.status = 'AWAITING_DETECTIVE'
            case.save(update_fields=['status'])
            
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
        
        return redirect('case_detail', pk=case_pk)
    
    return render(request, 'core/detective_request.html', {'case': case})


@login_required
def detective_dashboard(request):
    """Dashboard for detectives showing assigned cases and requests."""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_detective:
        messages.error(request, "Access denied. Detective privileges required.")
        return redirect('dashboard')
    
    # Get active assignments
    assignments = CaseAssignment.objects.filter(
        detective=request.user,
        status='ACTIVE'
    ).select_related('case')
    
    # Get pending requests
    pending_requests = DetectiveRequest.objects.filter(
        status='PENDING'
    ).select_related('case', 'requested_by')
    
    # Get achievements
    achievements = DetectiveAchievement.objects.filter(detective=request.user)
    
    context = {
        'assignments': assignments,
        'pending_requests': pending_requests,
        'achievements': achievements,
        'stats': {
            'active_cases': assignments.count(),
            'pending_requests': pending_requests.count(),
            'total_solved': DetectiveAchievement.objects.filter(
                detective=request.user,
                achievement_type='CASE_SOLVED'
            ).count()
        }
    }
    
    return render(request, 'core/detective_dashboard.html', context)


@login_required
def accept_case_assignment(request, request_pk):
    """Detective accepts a case assignment request."""
    det_request = get_object_or_404(DetectiveRequest, pk=request_pk)
    
    if not hasattr(request.user, 'profile') or not request.user.profile.is_detective:
        messages.error(request, "Access denied.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Update request status
                det_request.status = 'ACCEPTED'
                det_request.accepted_by = request.user
                det_request.save(update_fields=['status', 'accepted_by'])
                
                # Create assignment
                CaseAssignment.objects.create(
                    case=det_request.case,
                    detective=request.user,
                    assigned_by=det_request.requested_by,
                    status='ACTIVE'
                )
                
                # Update case status
                det_request.case.status = 'UNDER_INVESTIGATION'
                det_request.case.save(update_fields=['status'])
                
                messages.success(request, "Case assignment accepted!")
                
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
    
    return redirect('detective_dashboard')


@login_required
def submit_investigation_update(request, assignment_pk):
    """Detective submits investigation update with evidence."""
    assignment = get_object_or_404(CaseAssignment, pk=assignment_pk)
    
    if assignment.detective != request.user:
        messages.error(request, "Access denied.")
        return redirect('detective_dashboard')
    
    if request.method == 'POST':
        update_text = request.POST.get('update_text', '').strip()
        evidence_images = request.FILES.getlist('evidence_images')
        
        if not update_text and not evidence_images:
            messages.error(request, "Update text or evidence images required.")
            return redirect('detective_dashboard')
        
        try:
            update = InvestigationUpdate.objects.create(
                case_assignment=assignment,
                update_text=update_text,
                detective=request.user
            )
            
            for img in evidence_images:
                # Create CaseImage linked to the case for evidence
                CaseImage.objects.create(
                    case=assignment.case,
                    image=img,
                    is_evidence=True
                )
            
            messages.success(request, "Investigation update submitted!")
            
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
    
    return redirect('detective_dashboard')


@login_required
def mark_case_solved(request, case_pk):
    """Detective marks a case as solved."""
    case = get_object_or_404(Case, pk=case_pk)
    
    # Check if user is assigned detective
    assignment = CaseAssignment.objects.filter(
        case=case,
        detective=request.user,
        status='ACTIVE'
    ).first()
    
    if not assignment:
        messages.error(request, "Access denied.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        resolution_notes = request.POST.get('resolution_notes', '').strip()
        
        try:
            with transaction.atomic():
                case.status = 'SOLVED'
                case.resolution_notes = resolution_notes
                case.solved_at = timezone.now()
                case.save(update_fields=['status', 'resolution_notes', 'solved_at'])
                
                # Deactivate assignment
                assignment.status = 'COMPLETED'
                assignment.save(update_fields=['status'])
                
                # Create achievement
                DetectiveAchievement.objects.create(
                    detective=request.user,
                    case=case,
                    achievement_type='CASE_SOLVED',
                    description=f"Solved case: {case.title}"
                )
                
                messages.success(request, "Case marked as solved!")
                
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
    
    return redirect('case_detail', pk=case_pk)


# Admin Dashboard Views

@login_required
def admin_dashboard(request):
    """Admin dashboard for managing detective requests, verifications, and assignments."""
    if not request.user.is_superuser and not (hasattr(request.user, 'profile') and request.user.profile.is_admin):
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('dashboard')
    
    # Pending detective verification requests
    pending_verifications = Profile.objects.filter(
        is_detective=True,
        is_verified=False
    )
    
    # All detective requests
    all_det_requests = DetectiveRequest.objects.all().select_related(
        'case', 'requested_by', 'accepted_by'
    )
    
    # All case assignments
    all_assignments = CaseAssignment.objects.all().select_related(
        'case', 'detective', 'assigned_by'
    )
    
    # Statistics
    stats = {
        'total_cases': Case.objects.count(),
        'open_cases': Case.objects.filter(status='OPEN').count(),
        'solved_cases': Case.objects.filter(status='SOLVED').count(),
        'total_detectives': Profile.objects.filter(is_detective=True, is_verified=True).count(),
        'pending_verifications': pending_verifications.count()
    }
    
    context = {
        'pending_verifications': pending_verifications,
        'det_requests': all_det_requests,
        'assignments': all_assignments,
        'stats': stats
    }
    
    return render(request, 'core/admin_dashboard.html', context)


@login_required
def verify_detective(request, profile_pk):
    """Admin verifies a detective profile."""
    if not request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect('dashboard')
    
    profile = get_object_or_404(Profile, pk=profile_pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            profile.is_verified = True
            profile.save(update_fields=['is_verified'])
            messages.success(request, f"Detective {profile.user.username} verified!")
        elif action == 'reject':
            profile.is_detective = False
            profile.save(update_fields=['is_detective'])
            messages.success(request, f"Detective request for {profile.user.username} rejected.")
    
    return redirect('admin_dashboard')


@login_required
def assign_detective_manually(request, case_pk):
    """Admin manually assigns a detective to a case."""
    if not request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect('dashboard')
    
    case = get_object_or_404(Case, pk=case_pk)
    detectives = Profile.objects.filter(is_detective=True, is_verified=True).select_related('user')
    
    if request.method == 'POST':
        detective_id = request.POST.get('detective_id')
        
        if not detective_id:
            messages.error(request, "No detective selected.")
            return redirect('admin_dashboard')
        
        detective = get_object_or_404(Profile, pk=detective_id)
        
        try:
            with transaction.atomic():
                CaseAssignment.objects.create(
                    case=case,
                    detective=detective.user,
                    assigned_by=request.user,
                    status='ACTIVE'
                )
                
                case.status = 'UNDER_INVESTIGATION'
                case.save(update_fields=['status'])
                
                messages.success(request, "Detective assigned successfully!")
                
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
    
    return render(request, 'core/assign_detective.html', {
        'case': case,
        'detectives': detectives
    })


# API Endpoints

def map_data_api(request):
    """JSON API endpoint for Leaflet map with active case coordinates."""
    from django.conf import settings
    
    # Get active cases with coordinates
    active_cases = Case.objects.filter(
        status__in=['OPEN', 'UNDER_INVESTIGATION', 'AWAITING_DETECTIVE'],
        latitude__isnull=False,
        longitude__isnull=False
    ).select_related('user')[:100]  # Limit to 100 for performance
    
    features = []
    for case in active_cases:
        thumbnail = None
        first_image = case.images.first()
        if first_image:
            thumbnail = first_image.image.url
        
        features.append({
            'type': 'Feature',
            'properties': {
                'id': case.id,
                'title': case.title,
                'case_type': case.get_case_type_display(),
                'status': case.get_status_display(),
                'date_occurred': case.date_occurred.isoformat() if case.date_occurred else None,
                'thumbnail': thumbnail,
                'detail_url': f'/cases/{case.id}/'
            },
            'geometry': {
                'type': 'Point',
                'coordinates': [float(case.longitude), float(case.latitude)]
            }
        })
    
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }
    
    return JsonResponse(geojson)
