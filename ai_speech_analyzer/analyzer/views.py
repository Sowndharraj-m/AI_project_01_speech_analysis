import os
from django.shortcuts import render, redirect, get_object_or_404
from .models import SpeechAnalysis
from .forms import UploadSpeechForm
from .speech_analyzer import SpeechAnalyzer
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.decorators import login_required

@login_required(login_url='login')
def record_speech(request):
    if request.method == 'POST':
        form = UploadSpeechForm(request.POST, request.FILES)
        if form.is_valid():
            analysis = form.save()
            # If javascript MediaRecorder submits a file, it's captured here
            return redirect('analyze_speech', pk=analysis.pk)
        else:
            print("Form errors:", form.errors)
    else:
        form = UploadSpeechForm()
    
    return render(request, 'record.html', {'form': form})

@login_required(login_url='login')
def analyze_speech(request, pk):
    analysis = get_object_or_404(SpeechAnalysis, pk=pk)
    
    # if already analyzed
    if analysis.transcript:
        return redirect('results_dashboard', pk=pk)

    try:
        #get uploaded file path
        file_path = analysis.uploaded_file.path
    
        #check if file exists
        if not os.path.exists(file_path):
            print("File not found:",file_path)
            return redirect('results_dashboard', pk=pk)
        analyzer = SpeechAnalyzer(file_path)
        
        results = analyzer.analyze()
        
        # Clean up temporary converted WAV file
        analyzer.cleanup()
        
        # Save results
        analysis.transcript = results.get('transcript',"")
        analysis.speech_speed = results.get('speech_speed',0)
        analysis.filler_word_count = results.get('filler_word_count',0)
        analysis.pause_count = results.get('pause_count',0)
        analysis.voice_stability = results.get('voice_stability',0)
        analysis.confidence_score = results.get('confidence_score',0)
        # We can optionally save the score breakdown in a JSONField or related model,
        # but for simplicity we'll just reconstruct or rely on the total score
        analysis.save()
        
        return redirect('results_dashboard', pk=pk)
    except Exception as e:
        import traceback
        print(f"Error analyzing speech: {e}")
        traceback.print_exc()
        # In a real app we'd show an error message. For demo, just redirect to results (empty or partial).
        return redirect('results_dashboard', pk=pk)

@login_required(login_url='login')
def results_dashboard(request, pk):
    analysis = get_object_or_404(SpeechAnalysis, pk=pk)

    # Simplified suggestion logic
    suggestions = []
    if analysis.speech_speed > 160:
        suggestions.append("Slow down! You are speaking too fast.")
    elif analysis.speech_speed < 120:
        suggestions.append("Try to speak a little faster and more energetically.")
    
    if analysis.filler_word_count > 5:
        suggestions.append("You have too many filler words. Practice pausing instead of saying 'um' or 'uh'.")
    
    if analysis.pause_count < 2:
        suggestions.append("Use more pauses to emphasize points.")
        
    if analysis.voice_stability < 50:
        suggestions.append("Your voice volume isn't stable. Try to maintain a constant tone and volume.")

    # Re-calculate or hardcode the breakdown based on values:
    breakdown = {
        'speed': min(25, 25 - abs(140 - analysis.speech_speed) * 0.1),
        'filler': max(0, 25 - analysis.filler_word_count * 2.5),
        'pause': max(0, 25 - abs(10 - analysis.pause_count) * 1.5),
        'stability': min(25, (analysis.voice_stability / 100) * 25)
    }

    context = {
        'analysis': analysis,
        'suggestions': suggestions,
        'breakdown': breakdown,
    }
    return render(request, 'results.html', context)

@login_required(login_url='login')
def delete_speech(request, pk):
    if request.method == 'POST':
        analysis = get_object_or_404(SpeechAnalysis, pk=pk)
        analysis.delete()
    return redirect('speech_history')

@login_required(login_url='login')
def speech_history(request):
    history = SpeechAnalysis.objects.all().order_by('-created_at')
    return render(request, 'history.html', {'history': history})

import json
@login_required(login_url='login')
def improvement_dashboard(request):
    # Fetch all records ordered by date
    history = SpeechAnalysis.objects.all().order_by('created_at')
    
    # Format labels as "Speech X" + date, e.g. "Speech 1 (Mar 11)" for readability
    labels = []
    for i, h in enumerate(history, 1):
        date_str = h.created_at.strftime("%b %d")
        labels.append(f"Speech {i} ({date_str})")
        
    scores = [h.confidence_score for h in history]
    speeds = [h.speech_speed for h in history]
    
    # RADAR CHART CALCULATIONS: Latest vs Average (Normalized to 0-100 scales)
    def get_radar_stats(h):
        if not h: return [0, 0, 0, 0, 0]
        # Speed Score: 140 WPM is ideal.
        speed_score = max(0, 100 - abs(140 - h.speech_speed) * 0.8)
        # Filler Control: 0 is ideal. Each filler deducts 5 points.
        filler_score = max(0, 100 - (h.filler_word_count * 5))
        # Pause Usage Score: ~5 pauses is ideal.
        pause_score = max(0, 100 - abs(5 - h.pause_count) * 10)
        # Stability: 0-100 directly.
        stability_score = h.voice_stability
        # Confidence: 0-100 directly.
        conf_score = h.confidence_score
        return [speed_score, filler_score, pause_score, stability_score, conf_score]
        
    latest_radar = get_radar_stats(history.last())
    
    average_radar = [0, 0, 0, 0, 0]
    total_records = history.count()
    if total_records > 0:
        for h in history:
            st = get_radar_stats(h)
            for j in range(5):
                average_radar[j] += st[j]
        average_radar = [round(x / total_records, 1) for x in average_radar]

    context = {
        'labels': json.dumps(labels),
        'scores': json.dumps(scores),
        'speeds': json.dumps(speeds),
        'latest_radar': json.dumps(latest_radar),
        'average_radar': json.dumps(average_radar),
    }
    return render(request, 'dashboard.html', context)
