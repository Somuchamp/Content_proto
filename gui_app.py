import os
import sys

# Reconfigure standard output streams to use UTF-8 encoding to avoid Windows 'charmap' emoji crash
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass
if sys.stderr is not None:
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

# Enable High DPI Awareness on Windows for crystal-clear sharp text, fonts and canvas graphics
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except:
    try:
        windll.user32.SetProcessDPIAware()
    except:
        pass

import re
import json
import uuid
import queue
import asyncio
import threading
import webbrowser
import requests
import pandas as pd
from datetime import datetime
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment configuration from AppData folder
from app.config import ENV_PATH, ENV_DIR, APP_LOG_PATH
load_dotenv(dotenv_path=ENV_PATH)

# Application Versioning & Auto-Update Configuration
APP_VERSION = "1.0.6"
GITHUB_USER = os.getenv("GITHUB_USER", "Somuchamp")
GITHUB_REPO = os.getenv("GITHUB_REPO", "Content_proto")

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Import Backend Schema & Storage Entities
from app.models.schemas import (
    GeneratedContent, HeadingSection, ProcessedInsights, RefreshInterval, ContentType
)
from app.storage.file_storage import (
    save_content_json, save_keywords_csv, load_content_json,
    list_all_content_json, update_content_json, append_refresh_log_csv, _load_insights
)
from app.api.routes.content import _run_full_pipeline, url_scraper, processor, generator, _interval_to_hours
from app.services import dataforseo_service as ah

# Optional imports
try:
    from app.services.google_ads_keyword_planner import (
        fetch_keyword_planner_ideas, is_google_ads_planner_configured
    )
except ImportError:
    is_google_ads_planner_configured = lambda: False
    fetch_keyword_planner_ideas = lambda *args, **kwargs: ([], "Google Ads package not installed.")

# Theme Palette Colors (Obsidian and Glowing Cyan/Neon Theme)
BG_PRIMARY = "#0c0a1a"      # Deep obsidian space background
BG_SECONDARY = "#130f24"    # Sidebar background
BG_CONTAINER = "#1a162f"    # Dark purple-tinted container block
BG_BORDER = "#251e3b"       # Dark purple border
BG_TERTIARY = "#211b3b"     # Active button or tab color
ACCENT_CYAN = "#00f2fe"     # Glowing neon cyan
ACCENT_BLUE = "#38bdf8"     # Bright cyan-blue
ACCENT_PURPLE = "#a78bfa"   # Soft glowing purple
TEXT_MAIN = "#ffffff"       # Bold white headers/text
TEXT_MUTED = "#7c7793"      # Soft muted purple-gray text
ACCENT_GREEN = "#4ade80"    # Glowing status green
ACCENT_RED = "#f87171"      # Status red
ACCENT_YELLOW = "#facc15"   # Status warning yellow

def draw_rounded_rect(canvas, x1, y1, x2, y2, r, **kwargs):
    """Draws a pixel-perfect, razor-sharp rounded rectangle with hardware-accelerated GDI arcs."""
    fill = kwargs.get("fill", "")
    outline = kwargs.get("outline", "")
    width = kwargs.get("width", 1)
    
    w = x2 - x1
    h = y2 - y1
    r = min(r, w/2, h/2)
    if r < 1:
        return canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline, width=width)
        
    if fill:
        canvas.create_rectangle(x1 + r, y1, x2 - r, y2, fill=fill, outline="")
        canvas.create_rectangle(x1, y1 + r, x1 + r, y2 - r, fill=fill, outline="")
        canvas.create_rectangle(x2 - r, y1 + r, x2, y2 - r, fill=fill, outline="")
        canvas.create_arc(x1, y1, x1 + 2*r, y1 + 2*r, start=90, extent=90, style="pieslice", fill=fill, outline="")
        canvas.create_arc(x2 - 2*r, y1, x2, y1 + 2*r, start=0, extent=90, style="pieslice", fill=fill, outline="")
        canvas.create_arc(x2 - 2*r, y2 - 2*r, x2, y2, start=270, extent=90, style="pieslice", fill=fill, outline="")
        canvas.create_arc(x1, y2 - 2*r, x1 + 2*r, y2, start=180, extent=90, style="pieslice", fill=fill, outline="")
        
    if outline:
        canvas.create_line(x1 + r, y1, x2 - r, y1, fill=outline, width=width)
        canvas.create_line(x1 + r, y2, x2 - r, y2, fill=outline, width=width)
        canvas.create_line(x1, y1 + r, x1, y2 - r, fill=outline, width=width)
        canvas.create_line(x2, y1 + r, x2, y2 - r, fill=outline, width=width)
        canvas.create_arc(x1, y1, x1 + 2*r, y1 + 2*r, start=90, extent=90, style="arc", outline=outline, width=width)
        canvas.create_arc(x2 - 2*r, y1, x2, y1 + 2*r, start=0, extent=90, style="arc", outline=outline, width=width)
        canvas.create_arc(x2 - 2*r, y2 - 2*r, x2, y2, start=270, extent=90, style="arc", outline=outline, width=width)
        canvas.create_arc(x1, y2 - 2*r, x1 + 2*r, y2, start=180, extent=90, style="arc", outline=outline, width=width)

class CanvasEntry(tk.Frame):
    """A highly aesthetic custom text input field with a glowing cyan neon border."""
    def __init__(self, parent, placeholder="e.g., sustainable fashion trends", **kwargs):
        super().__init__(parent, bg=BG_BORDER, padx=1, pady=1, **kwargs)
        self.placeholder = placeholder
        self.is_focused = False
        self.hovered = False
        
        self.inner_frame = tk.Frame(self, bg="#1c1835", padx=12, pady=9)
        self.inner_frame.pack(fill="both", expand=True)
        
        # Embedded flat Entry widget
        self.entry = tk.Entry(self.inner_frame, bg="#1c1835", fg=TEXT_MUTED, bd=0, insertbackground=TEXT_MAIN, font=("Segoe UI", 10))
        self.entry.insert(0, placeholder)
        self.entry.pack(fill="x", expand=True)
        
        self.entry.bind("<FocusIn>", self.on_focus_in)
        self.entry.bind("<FocusOut>", self.on_focus_out)
        
        # Forward mouse click on the outer frames to the entry
        self.bind("<Button-1>", lambda e: self.entry.focus_set())
        self.inner_frame.bind("<Button-1>", lambda e: self.entry.focus_set())
        
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.inner_frame.bind("<Enter>", self.on_enter)
        self.inner_frame.bind("<Leave>", self.on_leave)
        
    def on_enter(self, event):
        self.hovered = True
        if not self.is_focused:
            self.configure(bg="#392f5c")
        
    def on_leave(self, event):
        self.hovered = False
        if not self.is_focused:
            self.configure(bg=BG_BORDER)
            
    def on_focus_in(self, event):
        self.is_focused = True
        self.configure(bg=ACCENT_CYAN) # Neon glow border
        if self.entry.get() == self.placeholder:
            self.entry.delete(0, tk.END)
            self.entry.configure(fg=TEXT_MAIN)
        
    def on_focus_out(self, event):
        self.is_focused = False
        self.configure(bg=BG_BORDER)
        if not self.entry.get().strip():
            self.entry.insert(0, self.placeholder)
            self.entry.configure(fg=TEXT_MUTED)
            
    def get(self):
        val = self.entry.get().strip()
        if val == self.placeholder:
            return ""
        return val
        
    def set(self, val):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, val)
        self.entry.configure(fg=TEXT_MAIN)

    def draw(self):
        pass

class CanvasDropdown(tk.Canvas):
    """A premium custom canvas-drawn dropdown replacing ugly native OS Comboboxes."""
    def __init__(self, parent, values=None, initial_index=0, left_icon="", right_icon="", callback=None, **kwargs):
        super().__init__(parent, height=44, bg=BG_SECONDARY, highlightthickness=0, bd=0, cursor="hand2", **kwargs)
        self.values = values or []
        self.current_idx = initial_index
        self.left_icon = left_icon
        self.right_icon = right_icon
        self.callback = callback
        self.hovered = False
        self.opened = False
        self.popup = None
        
        self.bind("<Button-1>", self.on_click)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Configure>", lambda e: self.draw())
        
    def on_enter(self, event):
        self.hovered = True
        self.draw()
        
    def on_leave(self, event):
        self.hovered = False
        self.draw()
        
    def get(self):
        if 0 <= self.current_idx < len(self.values):
            return self.values[self.current_idx]
        return ""
        
    def current(self, index=None):
        if index is None:
            return self.current_idx
        if 0 <= index < len(self.values):
            self.current_idx = index
            self.draw()
            if self.callback:
                self.callback(self.get())
                
    def set(self, value):
        if value in self.values:
            self.current_idx = self.values.index(value)
            self.draw()
            if self.callback:
                self.callback(value)
                
    def on_click(self, event):
        if self.opened:
            self.close_dropdown()
        else:
            self.show_dropdown()
            
    def show_dropdown(self):
        if not self.values:
            return
        self.opened = True
        self.draw()
        
        # Screen coordinates placement
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + 2
        w = self.winfo_width()
        
        # Capped height to fit screen with scrollbar
        h_popup = min(300, len(self.values) * 36 + 46)
        
        self.popup = tk.Toplevel(self)
        self.popup.overrideredirect(True)
        self.popup.geometry(f"{w}x{h_popup}+{x}+{y}")
        self.popup.configure(bg=BG_SECONDARY, highlightthickness=1, highlightbackground=BG_BORDER)
        
        # 1. Search filter box at the top
        search_frame = tk.Frame(self.popup, bg=BG_SECONDARY, padx=2, pady=2)
        search_frame.pack(fill="x", side="top", padx=5, pady=5)
        
        # Rounded capsule border for search box
        search_border = tk.Frame(search_frame, bg=BG_BORDER, padx=1, pady=1)
        search_border.pack(fill="x", expand=True)
        
        search_entry = tk.Entry(search_border, bg="#1c1835", fg=TEXT_MAIN, insertbackground=TEXT_MAIN, font=("Segoe UI", 9), bd=0)
        search_entry.pack(fill="x", expand=True, ipady=4, padx=8)
        search_entry.focus_set()
        
        # 2. Scrollable list container
        list_container = ttk.Frame(self.popup, style='TFrame')
        list_container.pack(fill="both", expand=True, padx=2, pady=(0, 5))
        
        scroll_view = ScrollableFrame(list_container)
        scroll_view.pack(fill="both", expand=True)
        
        # Select value helper
        def select_val(value):
            if value in self.values:
                self.current_idx = self.values.index(value)
                self.close_dropdown()
                if self.callback:
                    self.callback(value)
                    
        # Filter and render list items dynamically
        def update_list(event=None):
            # Clear old items
            for child in scroll_view.scrollable_frame.winfo_children():
                child.destroy()
                
            query = search_entry.get().strip().lower()
            filtered = [v for v in self.values if query in v.lower()]
            
            if not filtered:
                lbl = tk.Label(scroll_view.scrollable_frame, text="No matches found", fg=TEXT_MUTED, bg=BG_PRIMARY, font=("Segoe UI", 9, "italic"), anchor="w", padx=15, pady=8)
                lbl.pack(fill="x")
                return
                
            for val in filtered:
                is_active = (self.get() == val)
                item_fg = ACCENT_CYAN if is_active else TEXT_MAIN
                item_bg = "#1c1835" if is_active else BG_SECONDARY
                font_w = "bold" if is_active else "normal"
                
                lbl = tk.Label(scroll_view.scrollable_frame, text=val, fg=item_fg, bg=item_bg, font=("Segoe UI", 9, font_w), anchor="w", cursor="hand2", padx=15, pady=6)
                lbl.pack(fill="x")
                
                # Highlight on hover
                lbl.bind("<Enter>", lambda e, l=lbl, active=is_active: l.configure(bg="#1c1835", fg=ACCENT_CYAN))
                lbl.bind("<Leave>", lambda e, l=lbl, active=is_active: l.configure(bg="#1c1835" if active else BG_SECONDARY, fg=ACCENT_CYAN if active else TEXT_MAIN))
                
                # Handle selection click
                lbl.bind("<Button-1>", lambda e, v=val: select_val(v))
                
        # Bind search typing event
        search_entry.bind("<KeyRelease>", update_list)
        
        # Initial population of list
        update_list()
        
        # Handle focus-out and grabs safely
        self.popup.bind("<FocusOut>", lambda e: self.check_pop_focus(e))
        self.popup.grab_set()
        
    def check_pop_focus(self, event):
        # Prevent premature closing if user clicks within the search box or popup widgets
        focus_w = self.popup.focus_get()
        if focus_w and (focus_w == self.popup or focus_w.winfo_parent() == str(self.popup) or focus_w.winfo_toplevel() == self.popup):
            return
        self.close_dropdown()

    def close_dropdown(self):
        if self.popup:
            self.popup.destroy()
            self.popup = None
        self.opened = False
        self.draw()
        
    def draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = 44
        if w < 50:
            return
            
        bg_color = "#1c1835"
        border_color = ACCENT_CYAN if self.opened else (ACCENT_BLUE if self.hovered else BG_BORDER)
        
        draw_rounded_rect(self, 3, 3, w - 3, h - 3, 8, fill=bg_color, outline=border_color, width=1.5)
        
        curr_val = self.get()
        x_offset = 18
        if self.left_icon:
            self.create_text(x_offset, h/2, text=self.left_icon, fill=TEXT_MAIN, font=("Segoe UI", 12), anchor="w")
            x_offset += 25
            
        self.create_text(x_offset, h/2, text=curr_val, fill=TEXT_MAIN, font=("Segoe UI", 9, "bold"), anchor="w")
        
        if self.right_icon:
            self.create_text(w - 22, h/2, text=self.right_icon, fill=TEXT_MUTED, font=("Segoe UI", 12), anchor="e")
        else:
            chevron = "▲" if self.opened else "▼"
            self.create_text(w - 20, h/2, text=chevron, fill=TEXT_MUTED, font=("Segoe UI", 8), anchor="center")

class CanvasSlider(tk.Canvas):
    """A highly aesthetic neon progress-bar slider with circular glowing handle and soft neon halos."""
    def __init__(self, parent, from_=1, to=10, initial=5, callback=None, **kwargs):
        super().__init__(parent, height=50, bg=BG_CONTAINER, highlightthickness=0, bd=0, cursor="hand2", **kwargs)
        self.from_ = from_
        self.to = to
        self.value = initial
        self.callback = callback
        
        self.bind("<B1-Motion>", self.on_click)
        self.bind("<Button-1>", self.on_click)
        self.bind("<Configure>", lambda e: self.draw())
        
    def on_click(self, event):
        w = self.winfo_width()
        x = max(20, min(event.x, w - 20))
        pct = (x - 20) / (w - 40)
        self.value = self.from_ + pct * (self.to - self.from_)
        self.draw()
        if self.callback:
            self.callback(self.value)
            
    def get(self):
        return self.value
        
    def set(self, val):
        self.value = max(self.from_, min(val, self.to))
        self.draw()
        
    def draw(self):
        self.delete("all")
        w = self.winfo_width()
        if w < 100:
            return
        
        # Track line background
        self.create_line(20, 20, w - 20, 20, fill="#251e3b", width=6, capstyle="round")
        
        # Active glowing neon progress track
        pct = (self.value - self.from_) / (self.to - self.from_)
        active_x = 20 + pct * (w - 40)
        self.create_line(20, 20, active_x, 20, fill=ACCENT_CYAN, width=6, capstyle="round")
        
        # Fading concentric halos around the handle to simulate real neon glow
        self.create_oval(active_x - 18, 20 - 18, active_x + 18, 20 + 18, fill="", outline="#04222c", width=3)
        self.create_oval(active_x - 14, 20 - 14, active_x + 14, 20 + 14, fill="", outline="#083848", width=2)
        self.create_oval(active_x - 10, 20 - 10, active_x + 10, 20 + 10, fill="", outline="#00a3cc", width=1.5)
        
        # Glowing circular handle
        self.create_oval(active_x - 8, 20 - 8, active_x + 8, 20 + 8, fill="#ffffff", outline=ACCENT_CYAN, width=2)
        
        # Scale Labels underneath
        ticks = [1, 3, 5, 10]
        tick_labels = {1: "1", 3: "3", 5: "5", 10: "10+"}
        for t in ticks:
            t_pct = (t - self.from_) / (self.to - self.from_)
            t_x = 20 + t_pct * (w - 40)
            self.create_line(t_x, 24, t_x, 28, fill="#524a75", width=2)
            self.create_text(t_x, 38, text=tick_labels[t], fill=TEXT_MUTED, font=("Segoe UI", 9, "bold"))

class ResearchInputSwitch(tk.Canvas):
    """Capsule-style active toggle switch with glowing active state capsules."""
    def __init__(self, parent, callback=None, **kwargs):
        super().__init__(parent, height=44, bg=BG_CONTAINER, highlightthickness=0, bd=0, cursor="hand2", **kwargs)
        self.state = "keyword"
        self.callback = callback
        
        self.bind("<Button-1>", self.on_click)
        self.bind("<Configure>", lambda e: self.draw())
        
    def on_click(self, event):
        w = self.winfo_width()
        if event.x < w / 2:
            self.state = "keyword"
        else:
            self.state = "url"
        self.draw()
        if self.callback:
            self.callback(self.state)
            
    def draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = 44
        if w < 100:
            return
        
        # Background capsule shape
        draw_rounded_rect(self, 2, 2, w - 2, h - 2, 20, fill="#1c1835", outline=BG_BORDER, width=1)
        
        half = w / 2
        if self.state == "keyword":
            # Active glowing outline shadow
            for offset in range(3, 0, -1):
                draw_rounded_rect(self, 4-offset, 4-offset, half-2+offset, h-4+offset, 18, fill="", outline="#022a36" if offset==3 else ("#044254" if offset==2 else "#00f2fe"), width=offset)
            
            draw_rounded_rect(self, 4, 4, half - 2, h - 4, 18, fill=ACCENT_CYAN, outline="")
            self.create_text(half / 2, h / 2, text="KEYWORD RESEARCH", fill=BG_PRIMARY, font=("Segoe UI", 9, "bold"))
            self.create_text(half + half / 2, h / 2, text="URL-BASED RESEARCH", fill=TEXT_MUTED, font=("Segoe UI", 9, "bold"))
        else:
            # Active glowing outline shadow
            for offset in range(3, 0, -1):
                draw_rounded_rect(self, half+2-offset, 4-offset, w-4+offset, h-4+offset, 18, fill="", outline="#022a36" if offset==3 else ("#044254" if offset==2 else "#00f2fe"), width=offset)
                
            draw_rounded_rect(self, half + 2, 4, w - 4, h - 4, 18, fill=ACCENT_CYAN, outline="")
            self.create_text(half / 2, h / 2, text="KEYWORD RESEARCH", fill=TEXT_MUTED, font=("Segoe UI", 9, "bold"))
            self.create_text(half + half / 2, h / 2, text="URL-BASED RESEARCH", fill=BG_PRIMARY, font=("Segoe UI", 9, "bold"))

class ExecutePipelineButton(tk.Canvas):
    """Large, glowing action button with layered cyan neon halos matching the mockup."""
    def __init__(self, parent, text, command, **kwargs):
        super().__init__(parent, height=48, bg=BG_CONTAINER, highlightthickness=0, bd=0, cursor="hand2", **kwargs)
        self.text = text
        self.command = command
        self.hover = False
        
        self.bind("<Button-1>", lambda e: self.command())
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Configure>", lambda e: self.draw())
        
    def on_enter(self, event):
        self.hover = True
        self.draw()
        
    def on_leave(self, event):
        self.hover = False
        self.draw()
        
    def draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = 48
        if w < 50:
            return
        
        # Soft radiating cyan neon shadow
        for offset in range(4, 0, -1):
            draw_rounded_rect(self, 2-offset, 2-offset, w-2+offset, h-2+offset, 22, fill="", outline="#022430" if offset==4 else ("#043648" if offset==3 else ("#008fa8" if offset==2 else "#00f2fe")), width=offset)
            
        fill_color = ACCENT_BLUE if self.hover else ACCENT_CYAN
        draw_rounded_rect(self, 2, 2, w - 2, h - 2, 22, fill=fill_color, outline="")
        
        # bold dark text with waves symbol (|i|)
        self.create_text(w / 2, h / 2, text=f"{self.text}   (|i|)", fill=BG_PRIMARY, font=("Segoe UI", 10, "bold"))

class CanvasNavButton(tk.Canvas):
    """A premium custom canvas-drawn rounded navigation capsule button for the sidebar."""
    def __init__(self, parent, text, icon, command, **kwargs):
        super().__init__(parent, height=44, bg=BG_SECONDARY, highlightthickness=0, bd=0, cursor="hand2", **kwargs)
        self.text = text
        self.icon = icon
        self.command = command
        self.hovered = False
        self.active = False
        
        self.bind("<Button-1>", lambda e: self.command())
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Configure>", lambda e: self.draw())
        
    def on_enter(self, event):
        self.hovered = True
        self.draw()
        
    def on_leave(self, event):
        self.hovered = False
        self.draw()
        
    def set_active(self, active):
        self.active = active
        self.draw()
        
    def draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = 44
        if w < 50:
            return
            
        if self.active:
            bg_color = "#1c142c"
            border_color = ACCENT_CYAN
            fg_color = TEXT_MAIN
            draw_rounded_rect(self, 2, 2, w - 2, h - 2, 12, fill=bg_color, outline=border_color, width=1.5)
        elif self.hovered:
            bg_color = "#161225"
            border_color = "#392f5c"
            fg_color = ACCENT_CYAN
            draw_rounded_rect(self, 2, 2, w - 2, h - 2, 12, fill=bg_color, outline=border_color, width=1)
        else:
            bg_color = BG_SECONDARY
            fg_color = TEXT_MUTED
            draw_rounded_rect(self, 2, 2, w - 2, h - 2, 12, fill=bg_color, outline="")
            
        self.create_text(20, h/2, text=self.icon, fill=fg_color, font=("Segoe UI", 11), anchor="w")
        self.create_text(48, h/2, text=self.text, fill=fg_color, font=("Segoe UI", 9, "bold" if self.active else "normal"), anchor="w")

class ScrollableFrame(ttk.Frame):
    """Scroll view wrapper styled cleanly in dark obsidian."""
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0, bg=BG_PRIMARY)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", style="Vertical.TScrollbar", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas, style='TFrame')

        self.scrollable_frame.bind(
            "<Configure>",
            self.update_scrollregion
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.bind('<Configure>', self._on_canvas_configure)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        self.bind_mouse_wheel(self.canvas)
        
    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def update_scrollregion(self, event=None):
        bbox = self.canvas.bbox("all")
        if bbox:
            self.canvas.configure(scrollregion=(0, 0, bbox[2], bbox[3]))

    def bind_mouse_wheel(self, canvas):
        def _on_mousewheel(event):
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass
        
        def _bind(event):
            try:
                if canvas.winfo_exists():
                    canvas.bind_all("<MouseWheel>", _on_mousewheel)
            except Exception:
                pass
            
        def _unbind(event):
            try:
                canvas.unbind_all("<MouseWheel>")
            except Exception:
                pass
            
        canvas.bind("<Enter>", _bind)
        canvas.bind("<Leave>", _unbind)

def log_google_ads_error(err):
    try:
        from datetime import datetime
        appdata_base = os.getenv("LOCALAPPDATA") or os.path.expanduser("~")
        log_dir = os.path.join(appdata_base, "ContentStudioAI", "data")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "google_ads_error.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] {err}\n")
    except:
        pass

class ContentGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Content Studio AI")
        self.root.geometry("1300x820")
        self.root.configure(bg=BG_PRIMARY)

        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)

        # Deep Research cache stores
        self.dr_all_keywords = []

        self.setup_styles()
        self.create_layout()
        
        # Load Content Library Archive on Startup
        self.load_archive_list()
        
        # Schedule Asynchronous Auto-Update Check
        self.root.after(1000, self.start_update_check_thread)
        
    def on_exit(self):
        self.root.destroy()

    def start_update_check_thread(self):
        """Launches a background thread to check for application updates on GitHub Releases."""
        threading.Thread(target=self.check_for_updates, daemon=True).start()

    def check_for_updates(self):
        """Asynchronously checks GitHub Releases API for a newer version of the executable."""
        try:
            url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"
            headers = {"Accept": "application/vnd.github.v3+json"}
            # Send request with a short timeout to prevent boot hang
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                data = res.json()
                latest_version = data.get("tag_name", "").strip().lstrip("v")
                if not latest_version:
                    return
                
                # Compare versions using a robust numeric parser
                try:
                    current_parts = [int(x) for x in APP_VERSION.split(".")]
                    latest_parts = [int(x) for x in latest_version.split(".")]
                    # Normalize parts to equal lengths (e.g. [1, 0, 0] vs [1, 0, 1])
                    while len(current_parts) < len(latest_parts):
                        current_parts.append(0)
                    while len(latest_parts) < len(current_parts):
                        latest_parts.append(0)
                except Exception:
                    # Fallback to direct string check if parsing semantic version fails
                    if latest_version != APP_VERSION:
                        current_parts = [0]
                        latest_parts = [1]
                    else:
                        return

                if latest_parts > current_parts:
                    # Find the asset url for .exe
                    assets = data.get("assets", [])
                    exe_url = None
                    for asset in assets:
                        if asset.get("name", "").endswith(".exe"):
                            exe_url = asset.get("browser_download_url")
                            break
                    
                    if exe_url:
                        # Schedule UI display on the main Tkinter thread
                        changelog = data.get("body", "No release notes provided.")
                        self.root.after(0, lambda: self.show_update_dialog(latest_version, exe_url, changelog))
        except Exception as e:
            # Silent fallback
            pass

    def show_update_dialog(self, latest_version, exe_url, changelog):
        """Displays a premium custom update prompt modal aligned with Content Studio AI's neon styling."""
        dialog = tk.Toplevel(self.root)
        dialog.title("🚀 Update Available")
        dialog.geometry("520x450")
        dialog.configure(bg=BG_PRIMARY)
        dialog.resizable(False, False)
        
        # Make modal block other windows
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog relative to main window
        x = self.root.winfo_x() + (self.root.winfo_width() - 520) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 450) // 2
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
        
        # Aesthetic top neon line
        neon_line = tk.Frame(dialog, height=2, bg=ACCENT_CYAN)
        neon_line.pack(fill="x")
        
        content_frame = tk.Frame(dialog, bg=BG_PRIMARY, padx=30, pady=25)
        content_frame.pack(fill="both", expand=True)
        
        # Title with accent
        lbl_title = tk.Label(
            content_frame, 
            text="🚀 UPDATE DETECTED", 
            font=("Segoe UI", 16, "bold"), 
            fg=ACCENT_CYAN, 
            bg=BG_PRIMARY
        )
        lbl_title.pack(anchor="w", pady=(0, 10))
        
        # Description
        lbl_desc = tk.Label(
            content_frame, 
            text=f"A new version of Content Studio AI is ready to download.\n"
                 f"Current: v{APP_VERSION}   |   Latest: v{latest_version}",
            font=("Segoe UI", 10), 
            fg=TEXT_MAIN, 
            bg=BG_PRIMARY,
            justify="left"
        )
        lbl_desc.pack(anchor="w", pady=(0, 15))
        
        # Release Notes Label
        lbl_notes = tk.Label(
            content_frame, 
            text="What's New in this version:", 
            font=("Segoe UI", 9, "bold"), 
            fg=ACCENT_PURPLE, 
            bg=BG_PRIMARY
        )
        lbl_notes.pack(anchor="w", pady=(0, 5))
        
        # Control Buttons Panel - Packed FIRST at bottom so it is never pushed off screen
        btn_panel = tk.Frame(content_frame, bg=BG_PRIMARY)
        btn_panel.pack(fill="x", side="bottom", pady=(15, 0))
        
        # Progress bar (initially hidden) - Packed at bottom
        progress_frame = tk.Frame(content_frame, bg=BG_PRIMARY)
        
        # Release Notes Text Area (Scrollable text read-only) - Packed LAST with expand=True to occupy remaining space
        notes_frame = tk.Frame(content_frame, bg=BG_SECONDARY, bd=1, highlightbackground=BG_BORDER, highlightthickness=1)
        notes_frame.pack(fill="both", expand=True, pady=(0, 5))
        
        from tkinter import scrolledtext
        notes_text = scrolledtext.ScrolledText(
            notes_frame, 
            bg=BG_SECONDARY, 
            fg=TEXT_MAIN, 
            bd=0, 
            highlightthickness=0,
            insertbackground=TEXT_MAIN,
            font=("Segoe UI", 9),
            padx=10,
            pady=10
        )
        notes_text.pack(fill="both", expand=True)
        notes_text.insert("1.0", changelog)
        notes_text.configure(state="disabled")
        
        def start_download():
            btn_panel.pack_forget()
            progress_frame.pack(fill="x", side="bottom", pady=10)
            
            lbl_progress = tk.Label(progress_frame, text="📥 Downloading update (0%)...", font=("Segoe UI", 9), fg=ACCENT_CYAN, bg=BG_PRIMARY)
            lbl_progress.pack(anchor="w")
            
            progress_bar = ttk.Progressbar(progress_frame, style="Horizontal.TProgressbar", length=400, mode="determinate")
            progress_bar.pack(fill="x", pady=(5, 0))
            
            # Start actual download in a separate thread to keep UI alive
            threading.Thread(target=self.perform_update, args=(exe_url, latest_version, lbl_progress, progress_bar, dialog), daemon=True).start()
            
        btn_update = self.create_modern_button(btn_panel, "🚀 UPDATE NOW", start_download, primary=True)
        btn_update.pack(side="right", padx=(10, 0))
        
        btn_cancel = self.create_modern_button(btn_panel, "✖️ SKIP VERSION", dialog.destroy)
        btn_cancel.pack(side="right")
        
        # Configure local style for custom neon progress bar in dialog
        style = ttk.Style()
        style.configure("Horizontal.TProgressbar", thickness=8, troughcolor=BG_SECONDARY, background=ACCENT_CYAN, borderwidth=0)

    def perform_update(self, exe_url, latest_version, lbl_progress, progress_bar, dialog):
        """Downloads the compiled .exe file and runs the local replacement updater script."""
        try:
            import urllib.request
            import tempfile
            import time
            import subprocess
            
            # Step 1: Set up path for temporary download file
            temp_dir = tempfile.gettempdir()
            new_exe_name = f"Content_Studio_AI_{latest_version}.exe"
            temp_exe_path = os.path.join(temp_dir, new_exe_name)
            
            # Request wrapper with progress callback
            def report_hook(block_num, block_size, total_size):
                if total_size > 0:
                    percent = min(100, int(block_num * block_size * 100 / total_size))
                    # Update progress UI thread-safely
                    self.root.after(0, lambda: progress_bar.configure(value=percent))
                    self.root.after(0, lambda: lbl_progress.configure(text=f"📥 Downloading update ({percent}%)..."))
            
            # Download file in chunks
            urllib.request.urlretrieve(exe_url, temp_exe_path, report_hook)
            
            # Step 2: Create batch script to replace current running executable
            current_exe = sys.executable
            is_compiled = getattr(sys, 'frozen', False)
            
            if not is_compiled:
                # In development mode, mock successful update instead of replacing python.exe!
                self.root.after(0, lambda: lbl_progress.configure(text="✅ Update ready! (Development mode: skipped replacement)."))
                time.sleep(2)
                self.root.after(0, dialog.destroy)
                return

            self.root.after(0, lambda: lbl_progress.configure(text="⚡ Applying update & restarting..."))
            
            updater_bat_path = os.path.join(temp_dir, "content_studio_updater.bat")
            
            bat_content = f"""@echo off
title Content Studio AI - Applying Update
echo Waiting for application to close...
timeout /t 2 /nobreak > nul
echo Overwriting with latest update version...
copy /y "{temp_exe_path}" "{current_exe}"
echo Starting new application version...
start "" "{current_exe}"
del "%~f0"
"""
            with open(updater_bat_path, "w", encoding="utf-8") as f:
                f.write(bat_content)
                
            # Step 3: Trigger batch execution asynchronously
            subprocess.Popen([updater_bat_path], shell=True)
            
            # Step 4: Terminate the application immediately so batch script can write
            self.root.after(100, self.on_exit)
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Update Error", f"Failed to apply update: {e}"))
            self.root.after(0, dialog.destroy)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure Dark Slate Aesthetics
        style.configure('.', background=BG_PRIMARY, foreground=TEXT_MAIN, font=('Segoe UI', 10))
        style.configure('TFrame', background=BG_PRIMARY)
        style.configure('Secondary.TFrame', background=BG_SECONDARY)
        style.configure('TLabel', background=BG_PRIMARY, foreground=TEXT_MAIN)
        style.configure('Secondary.TLabel', background=BG_SECONDARY, foreground=TEXT_MAIN)
        style.configure('Muted.TLabel', background=BG_PRIMARY, foreground=TEXT_MUTED)
        style.configure('SecondaryMuted.TLabel', background=BG_SECONDARY, foreground=TEXT_MUTED)
        style.configure('Header.TLabel', font=('Segoe UI', 17, 'bold'), foreground=TEXT_MAIN)
        style.configure('Subheader.TLabel', font=('Segoe UI', 12, 'bold'), foreground=ACCENT_PURPLE)
        style.configure('Subtitle.TLabel', font=('Segoe UI', 10), foreground=TEXT_MUTED)
        
        # Modern Scrollbars
        style.configure('Vertical.TScrollbar', background=BG_SECONDARY, troughcolor=BG_PRIMARY, borderwidth=0, arrowsize=8)
        style.map('Vertical.TScrollbar', background=[('active', BG_TERTIARY)])
        
        # Combobox / Entry style updates
        style.configure('TCombobox', fieldbackground=BG_CONTAINER, background=BG_PRIMARY, foreground=TEXT_MAIN, arrowcolor=ACCENT_CYAN, borderwidth=1, bordercolor=BG_BORDER)
        style.map('TCombobox', fieldbackground=[('readonly', BG_CONTAINER)], foreground=[('readonly', TEXT_MAIN)])
        style.configure('TEntry', fieldbackground=BG_CONTAINER, foreground=TEXT_MAIN, insertcolor=TEXT_MAIN, borderwidth=0)
        
        # Modern Horizontal Slider Scale
        style.configure('Horizontal.TScale', background=BG_PRIMARY, troughcolor=BG_SECONDARY, sliderlength=16, sliderthickness=16, borderwidth=0)
        style.map('Horizontal.TScale', background=[('active', ACCENT_CYAN)])

        # Treeview configured for tables
        style.configure('Treeview', background=BG_SECONDARY, fieldbackground=BG_SECONDARY, foreground=TEXT_MAIN, borderwidth=0, rowheight=30, font=('Segoe UI', 9))
        style.configure('Treeview.Heading', background=BG_TERTIARY, foreground=TEXT_MAIN, borderwidth=0, font=('Segoe UI', 10, 'bold'))
        style.map('Treeview', background=[('selected', BG_TERTIARY)])

    # Helper Creators for High-End Custom Styled Widgets
    def create_modern_entry(self, parent, placeholder="e.g., sustainable fashion trends"):
        """Creates a custom, active-highlight flat Entry field with padded borders."""
        border_frame = tk.Frame(parent, bg=BG_BORDER, padx=1, pady=1)
        inner_frame = tk.Frame(border_frame, bg=BG_CONTAINER, padx=12, pady=10)
        inner_frame.pack(fill="x", expand=True)

        ent = tk.Entry(inner_frame, bg=BG_CONTAINER, fg=TEXT_MUTED, bd=0, insertbackground=TEXT_MAIN, font=("Segoe UI", 10))
        ent.insert(0, placeholder)
        ent.pack(fill="x", expand=True)

        def on_focus_in(event):
            border_frame.configure(bg=ACCENT_CYAN)
            if ent.get() == placeholder:
                ent.delete(0, tk.END)
                ent.configure(fg=TEXT_MAIN)
        def on_focus_out(event):
            border_frame.configure(bg=BG_BORDER)
            if not ent.get().strip():
                ent.insert(0, placeholder)
                ent.configure(fg=TEXT_MUTED)

        ent.bind("<FocusIn>", on_focus_in)
        ent.bind("<FocusOut>", on_focus_out)
        
        border_frame.entry = ent
        return border_frame

    def create_modern_button(self, parent, text, command, primary=False, danger=False):
        """Creates an elegant flat button with responsive hover mappings."""
        bg_color = ACCENT_CYAN if primary else ("#7f1d1d" if danger else BG_SECONDARY)
        fg_color = BG_PRIMARY if primary else TEXT_MAIN
        hover_bg = ACCENT_BLUE if primary else ("#991b1b" if danger else BG_TERTIARY)
        hover_fg = BG_PRIMARY if primary else ACCENT_CYAN

        btn = tk.Button(
            parent, text=text, font=("Segoe UI", 9, "bold"),
            fg=fg_color, bg=bg_color, activebackground=hover_bg,
            activeforeground=hover_fg, bd=0, relief="flat", cursor="hand2",
            padx=16, pady=9, command=command
        )
        
        btn.bind("<Enter>", lambda e: btn.configure(bg=hover_bg, fg=hover_fg))
        btn.bind("<Leave>", lambda e: btn.configure(bg=bg_color, fg=fg_color))
        return btn

    def create_compact_button(self, parent, text, command):
        """Creates a compact modern button for section tools using standard colors."""
        btn = tk.Button(
            parent, text=text, font=("Segoe UI", 8, "bold"),
            fg=TEXT_MAIN, bg=BG_SECONDARY, activebackground=BG_TERTIARY,
            activeforeground=ACCENT_CYAN, bd=0, relief="flat", cursor="hand2",
            padx=8, pady=4, command=command
        )
        btn.bind("<Enter>", lambda e: btn.configure(bg=BG_TERTIARY, fg=ACCENT_CYAN))
        btn.bind("<Leave>", lambda e: btn.configure(bg=BG_SECONDARY, fg=TEXT_MAIN))
        return btn

    def copy_to_clipboard(self, text, button_widget):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()
        button_widget.configure(text="✅ Copied!")
        self.root.after(1500, lambda: button_widget.configure(text="📋 Copy"))

    def copy_full_article(self, text, button_widget):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()
        button_widget.configure(text="✅ Copied Full Article!")
        self.root.after(1500, lambda: button_widget.configure(text="📋 Copy Full Article"))


    def create_layout(self):
        # Root layout padding wrapper for high-fidelity space gaps
        wrapper = tk.Frame(self.root, bg=BG_PRIMARY, padx=12, pady=12)
        wrapper.pack(fill="both", expand=True)

        # 1. Left Navigation Sidebar Frame
        self.sidebar_border = tk.Frame(wrapper, bg=BG_BORDER, padx=1, pady=1)
        self.sidebar_border.pack(side="left", fill="y", padx=(0, 12))

        self.sidebar = tk.Frame(self.sidebar_border, bg=BG_SECONDARY, width=240)
        self.sidebar.pack(fill="y", expand=True)
        self.sidebar.pack_propagate(False)

        logo_lbl = tk.Label(self.sidebar, text="✦ Content Studio AI", font=("Segoe UI", 16, "bold"), fg=TEXT_MAIN, bg=BG_SECONDARY)
        logo_lbl.pack(pady=(30, 25), padx=20, anchor="w")

        # Sidebar navigation buttons list
        self.nav_items = {}
        pages = [
            ("Configure Pipeline", "pipeline"),
            ("Strategy Vault", "library"),
            ("Research Hub", "research"),
            ("Competitor Insights", "competitors"),
            ("Settings", "settings")
        ]

        menu_icons = {
            "Configure Pipeline": "🎛️",
            "Strategy Vault": "🗂️",
            "Research Hub": "🔬",
            "Competitor Insights": "🔍",
            "Settings": "⚙️"
        }

        for text, key in pages:
            icon = menu_icons.get(text, "✦")
            btn = CanvasNavButton(self.sidebar, text=text, icon=icon, command=lambda k=key: self.show_page(k))
            btn.pack(fill="x", padx=15, pady=5)
            self.nav_items[key] = btn

        # Health/Backend Status Indicators (Bottom Left Status indicator with a small green glowing dot)
        status_frame = tk.Frame(self.sidebar, bg=BG_SECONDARY)
        status_frame.pack(side="bottom", fill="x", pady=25, padx=25)
        
        self.status_dot = tk.Label(status_frame, text="●", fg=ACCENT_GREEN, bg=BG_SECONDARY, font=("Segoe UI", 12))
        self.status_dot.pack(side="left")
        status_text = tk.Label(status_frame, text=" API Core: Connected", fg=TEXT_MUTED, bg=BG_SECONDARY, font=("Segoe UI", 9, "bold"))
        status_text.pack(side="left")

        # 2. Main Content viewport area Frame
        self.viewport_border = tk.Frame(wrapper, bg=BG_BORDER, padx=1, pady=1)
        self.viewport_border.pack(side="right", fill="both", expand=True)

        self.viewport = tk.Frame(self.viewport_border, bg=BG_PRIMARY)
        self.viewport.pack(fill="both", expand=True)

        # Compile Pages
        self.pages = {}
        self.pages["pipeline"] = self.build_pipeline_page()
        self.pages["library"] = self.build_library_page()
        self.pages["research"] = self.build_research_page()
        self.pages["competitors"] = self.build_competitors_page()
        self.pages["settings"] = self.build_settings_page()

        # Show first page by default
        self.show_page("pipeline")

    def on_menu_hover(self, btn, frame, is_enter):
        pass

    def show_page(self, page_key):
        self.current_page = page_key
        for key, btn in self.nav_items.items():
            self.pages[key].pack_forget()
            btn.set_active(False)

        self.pages[page_key].pack(expand=True, fill="both")
        self.nav_items[page_key].set_active(True)

        # Force scroll position to the top of the page on switch
        if page_key == "pipeline" and hasattr(self, "pl_scroll"):
            self.pl_scroll.canvas.yview_moveto(0.0)
        elif page_key == "library" and hasattr(self, "lib_scroll"):
            self.lib_scroll.canvas.yview_moveto(0.0)
        elif page_key == "research" and hasattr(self, "dr_scroll"):
            self.dr_scroll.canvas.yview_moveto(0.0)
        elif page_key == "competitors" and hasattr(self, "ca_scroll"):
            self.ca_scroll.canvas.yview_moveto(0.0)

        # Dynamic loads for list updates
        if page_key == "library":
            self.load_archive_list()
        elif page_key == "settings":
            self.refresh_log_preview()

    # ─────────────────────────────────────────────────────────────────────────
    # BACKGROUND PIPELINE THREADING HELPERS
    # ─────────────────────────────────────────────────────────────────────────
    def run_threaded_task(self, task_func, args=(), success_cb=None, err_cb=None):
        def worker():
            try:
                res = task_func(*args)
                if success_cb:
                    self.root.after(0, success_cb, res)
            except Exception as e:
                if err_cb:
                    self.root.after(0, err_cb, e)
                else:
                    self.root.after(0, lambda: messagebox.showerror("Engine Failure", str(e)))
        
        threading.Thread(target=worker, daemon=True).start()

    def run_threaded_async(self, async_coro, success_cb=None, err_cb=None):
        def worker():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                res = loop.run_until_complete(async_coro)
                loop.close()
                if success_cb:
                    self.root.after(0, success_cb, res)
            except Exception as e:
                if err_cb:
                    self.root.after(0, err_cb, e)
                else:
                    self.root.after(0, lambda: messagebox.showerror("Execution Error", str(e)))
                    
        threading.Thread(target=worker, daemon=True).start()

    def fetch_and_set_image(self, url, label_widget):
        def worker():
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                response = requests.get(url, timeout=5, headers=headers)
                if response.status_code == 200:
                    from io import BytesIO
                    from PIL import Image, ImageTk
                    img_data = Image.open(BytesIO(response.content))
                    # Scale to fit container beautifully
                    img_data.thumbnail((120, 90), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img_data)
                    
                    label_widget.photo = photo
                    self.root.after(0, lambda: label_widget.configure(image=photo, text=""))
            except Exception as e:
                pass

        threading.Thread(target=worker, daemon=True).start()

    # --- PAGE 1: CONFIGURE PIPELINE ---
    def build_pipeline_page(self):
        page = ttk.Frame(self.viewport, style='TFrame')
        
        # Header Area
        lbl_frame = ttk.Frame(page, style='TFrame')
        lbl_frame.pack(fill="x", padx=30, pady=25)
        ttk.Label(lbl_frame, text="CONTENT PIPELINE", style='Header.TLabel').pack(anchor="w")
        ttk.Label(lbl_frame, text="Configure and launch AI-driven content research and generation", style='Subtitle.TLabel').pack(anchor="w", pady=(5, 0))

        # Scroll View for Dynamic Config Form
        self.pl_scroll = ScrollableFrame(page)
        self.pl_scroll.pack(fill="both", expand=True, padx=30, pady=10)
        
        self.pl_container = self.pl_scroll.scrollable_frame
        
        # Large Rounded purple-tinted container block matching mockup
        self.pl_form_card = tk.Frame(self.pl_container, bg=BG_CONTAINER, highlightthickness=1, highlightbackground=BG_BORDER)
        self.pl_form_card.pack(fill="x", side="top", padx=5, pady=5)
        
        # 1. RESEARCH INPUT CAPSULE SWITCH
        tk.Label(self.pl_form_card, text="RESEARCH INPUT", font=("Segoe UI", 9, "bold"), fg=TEXT_MAIN, bg=BG_CONTAINER).pack(anchor="w", padx=25, pady=(20, 5))
        
        self.pl_switch = ResearchInputSwitch(self.pl_form_card, callback=self.switch_pl_input_tab)
        self.pl_switch.pack(fill="x", padx=25, pady=2)
        
        # Interactive content subframes
        self.pl_input_tab = "keyword"
        
        # Standard Keyword Input Panel
        self.pl_std_frame = ttk.Frame(self.pl_form_card, style='Secondary.TFrame')
        self.pl_std_frame.pack(fill="x", padx=25, pady=5)
        
        # Keyword form input
        tk.Label(self.pl_std_frame, text="KEYWORD RESEARCH", font=("Segoe UI", 9, "bold"), fg=TEXT_MAIN, bg=BG_SECONDARY).pack(anchor="w", pady=(10, 2))
        self.ent_pl_name = CanvasEntry(self.pl_std_frame, "e.g., sustainable fashion trends")
        self.ent_pl_name.pack(fill="x", pady=2)

        # URL Input Panel
        self.pl_url_frame = ttk.Frame(self.pl_form_card, style='Secondary.TFrame')
        
        # URL form input
        tk.Label(self.pl_url_frame, text="URL-BASED RESEARCH", font=("Segoe UI", 9, "bold"), fg=TEXT_MAIN, bg=BG_SECONDARY).pack(anchor="w", pady=(10, 2))
        self.url_txt_border = tk.Frame(self.pl_url_frame, bg=BG_BORDER, padx=1, pady=1)
        self.url_txt_border.pack(fill="x", pady=2)
        self.txt_pl_urls = tk.Text(self.url_txt_border, bg=BG_CONTAINER, fg=TEXT_MAIN, bd=0, insertbackground=TEXT_MAIN, height=6, font=("Segoe UI", 10))
        self.txt_pl_urls.pack(fill="x", expand=True, padx=5, pady=5)
        
        # 2 columns layout under input field
        self.pl_cols_frame = ttk.Frame(self.pl_form_card, style='Secondary.TFrame')
        self.pl_cols_frame.pack(fill="x", padx=25, pady=10)
        
        # Left Column: CONTENT STRATEGY Dropdown
        col_left = ttk.Frame(self.pl_cols_frame, style='Secondary.TFrame')
        col_left.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        tk.Label(col_left, text="CONTENT STRATEGY", font=("Segoe UI", 9, "bold"), fg=TEXT_MAIN, bg=BG_SECONDARY).pack(anchor="w", pady=2)
        self.cmb_pl_strategy = CanvasDropdown(col_left, values=["Category Page", "Brand Page", "Blog / Keyword Article"], initial_index=0, left_icon="📂")
        self.cmb_pl_strategy.pack(fill="x", pady=2)
        
        # Right Column: TARGET MARKET Dropdown with country emoji flag
        col_right = ttk.Frame(self.pl_cols_frame, style='Secondary.TFrame')
        col_right.pack(side="right", fill="x", expand=True)
        
        tk.Label(col_right, text="TARGET MARKET (COUNTRY)", font=("Segoe UI", 9, "bold"), fg=TEXT_MAIN, bg=BG_SECONDARY).pack(anchor="w", pady=2)
        self.cmb_pl_country = CanvasDropdown(col_right, values=["United States", "United Kingdom", "Canada", "Australia", "India", "Germany", "Saudi Arabia", "United Arab Emirates"], initial_index=0, left_icon="🇺🇸")
        self.cmb_pl_country.pack(fill="x", pady=2)

        # Content depth slider
        tk.Label(self.pl_form_card, text="CONTENT DEPTH", font=("Segoe UI", 9, "bold"), fg=TEXT_MAIN, bg=BG_CONTAINER).pack(anchor="w", padx=25, pady=(15, 2))
        self.sl_pl_depth = CanvasSlider(self.pl_form_card, from_=1, to=10, initial=5)
        self.sl_pl_depth.pack(fill="x", padx=25, pady=2)



        # Glowing Neon execute button at the bottom center
        self.btn_pl_generate = ExecutePipelineButton(self.pl_form_card, "EXECUTE CONTENT PIPELINE", self.handle_pl_generate)
        self.btn_pl_generate.pack(fill="x", padx=25, pady=25)

        # Loading Indicator & Processing Logs
        self.pl_status_frame = ttk.Frame(self.pl_container, style='TFrame')
        self.pl_status_lbl = ttk.Label(self.pl_status_frame, text="🤖 Processing pipeline...", style='Subheader.TLabel')
        self.pl_status_lbl.pack(pady=10)
        self.pl_progress = ttk.Progressbar(self.pl_status_frame, mode='indeterminate', length=300)
        self.pl_progress.pack(pady=5)

        # Synthetic Content Results Frame
        self.pl_results_container = ttk.Frame(self.pl_container, style='TFrame')

        return page

    def switch_pl_input_tab(self, state_key):
        self.pl_input_tab = state_key
        if state_key == "keyword":
            self.pl_url_frame.pack_forget()
            self.pl_std_frame.pack(fill="x", padx=25, pady=5, before=self.pl_cols_frame)
        else:
            self.pl_std_frame.pack_forget()
            self.pl_url_frame.pack(fill="x", padx=25, pady=5, before=self.pl_cols_frame)

    def switch_pl_tab(self, tab_key):
        # Compatibility override for toolbar
        pass



    def show_pl_loading(self, show=True, text="🤖 Generating SEO Content..."):
        if show:
            self.pl_form_card.pack_forget()
            self.pl_results_container.pack_forget()
            self.pl_status_frame.pack(fill="x", pady=40)
            self.pl_status_lbl.configure(text=text)
            self.pl_progress.start(10)
        else:
            self.pl_progress.stop()
            self.pl_status_frame.pack_forget()
            self.pl_form_card.pack(fill="x", side="top", padx=5, pady=5)

    def handle_pl_generate(self):
        strategy_mapped = {
            "Category Page": "category",
            "Brand Page": "brand",
            "Blog / Keyword Article": "keyword"
        }[self.cmb_pl_strategy.get()]
        
        country = self.cmb_pl_country.get()

        depth = int(self.sl_pl_depth.get())
        interval = RefreshInterval.weekly
        custom_hrs = None

        # Multi-tab logic selector
        if self.pl_input_tab == "keyword":
            name = self.ent_pl_name.entry.get().strip()
            if not name or name == "e.g., sustainable fashion trends":
                messagebox.showwarning("Incomplete Fields", "Please supply target keyword.")
                return

            self.show_pl_loading(True, f"📝 Running multi-source analysis and generating content for {name}...")

            async def run_pipeline():
                return await _run_full_pipeline(
                    name=name,
                    content_type=strategy_mapped,
                    country=country,
                    max_headings=depth,
                    refresh_interval=interval,
                    custom_interval_hours=custom_hrs
                )

            def on_success(content: GeneratedContent):
                self.show_pl_loading(False)
                self.render_generated_results(content.model_dump(), self.pl_results_container)
                self.pl_results_container.pack(fill="x", side="top", pady=10)
                messagebox.showinfo("Success", f"Synthesis complete! Saved report: {content.name}")

            def on_error(err):
                self.show_pl_loading(False)
                messagebox.showerror("Pipeline Failed", str(err))

            self.run_threaded_async(run_pipeline(), on_success, on_error)
        else:
            # URL Scraping
            raw_urls = self.txt_pl_urls.get("1.0", tk.END).strip().split("\n")
            urls = [u.strip() for u in raw_urls if u.strip().startswith("http")]
            name = self.ent_pl_name.entry.get().strip() # Re-use search field or active strategy label
            if name == "e.g., sustainable fashion trends":
                name = "URL Mapped Content"

            if not urls:
                messagebox.showwarning("Missing URLs", "Please enter at least one valid source URL.")
                return

            self.show_pl_loading(True, f"🔗 Scraping {len(urls)} URLs and generating content...")

            async def run_url_pipeline():
                scraped_texts = await url_scraper.scrape_urls_concurrently(urls)
                if not scraped_texts:
                    raise Exception("Failed to extract meaningful text from URLs.")
                context_text = "\n\n---\n\n".join(scraped_texts)[:20000]
                
                insights = processor.process(
                    name=name,
                    content_type=strategy_mapped,
                    country=country,
                    context=context_text,
                    all_items=[],
                    serp_related=[],
                    serp_paa=[],
                    serp_pas=[],
                    autocomplete=[]
                )
                sections = generator.generate(
                    name=name,
                    content_type=strategy_mapped,
                    country=country,
                    insights=insights,
                    context=context_text,
                    max_headings=depth
                )

                cid = str(uuid.uuid4())
                now = datetime.utcnow()
                content = GeneratedContent(
                    id=cid,
                    name=name,
                    content_type=strategy_mapped,
                    country=country,
                    sections=sections,
                    insights=insights,
                    sources_used=["url_scraper"],
                    source_urls=urls,
                    created_at=now,
                    refresh_interval=RefreshInterval.weekly,
                    custom_interval_hours=None,
                    next_refresh_at=None
                )

                save_content_json(content)
                save_keywords_csv(cid, name, country, insights, urls)
                return content

            def on_success(content: GeneratedContent):
                self.show_pl_loading(False)
                self.render_generated_results(content.model_dump(), self.pl_results_container)
                self.pl_results_container.pack(fill="x", side="top", pady=10)
                messagebox.showinfo("Success", f"URL synthesis complete! Saved report: {content.name}")

            def on_error(err):
                self.show_pl_loading(False)
                messagebox.showerror("Pipeline Failed", str(err))

            self.run_threaded_async(run_url_pipeline(), on_success, on_error)

    # --- GENERAL RENDERER FOR DOCUMENT RESULTS ---
    def render_generated_results(self, data, container_frame):
        # Clean current contents
        for child in container_frame.winfo_children():
            child.destroy()

        header_frame = ttk.Frame(container_frame, style='TFrame')
        header_frame.pack(fill="x", pady=10)

        # Title + Type Badge
        badge = " [BLOG]" if data.get("content_type") == "keyword" else ""
        ttk.Label(header_frame, text=f"📋 {data['name']}{badge}", style='Header.TLabel').pack(anchor="w")
        
        created_val = data.get('created_at', '')
        if isinstance(created_val, datetime):
            created_str = created_val.strftime('%Y-%m-%d %H:%M:%S')
        else:
            created_str = str(created_val)[:19]

        info_str = f"Strategy: {data['content_type'].capitalize()}  |  Country: {data['country']}  |  Refreshed: {data['refresh_interval']}  |  Created: {created_str}"
        ttk.Label(header_frame, text=info_str, style='Subtitle.TLabel').pack(anchor="w", pady=2)

        # Export Buttons
        btn_frame = ttk.Frame(container_frame, style='TFrame')
        btn_frame.pack(fill="x", pady=5)
        
        sections = data.get("sections", [])
        full_article_text = ""
        for s_idx, sec in enumerate(sections, 1):
            full_article_text += f"## {s_idx}. {sec['heading']}\n\n{sec.get('body', '')}\n\n"
        
        self.create_modern_button(btn_frame, "📥 Save JSON Report", lambda: self.save_json_dialog(data), primary=True).pack(side="left", padx=(0, 10))
        self.create_modern_button(btn_frame, "📊 Save Keywords CSV", lambda: self.save_csv_dialog(data)).pack(side="left")
        
        full_article_copy_btn = self.create_modern_button(btn_frame, "📋 Copy Full Article", None)
        full_article_copy_btn.configure(command=lambda t=full_article_text, btn=full_article_copy_btn: self.copy_full_article(t, btn))
        full_article_copy_btn.pack(side="left", padx=(10, 0))

        # Metrics display panels
        insights = data.get("insights", {})
        
        metrics_frame = ttk.Frame(container_frame, style='TFrame')
        metrics_frame.pack(fill="x", pady=15)
        
        metrics_data = [
            ("Keywords", len(insights.get("keywords", []))),
            ("Autocomplete", len(insights.get("autocomplete_keywords", []))),
            ("PAA Queries", len(insights.get("people_also_ask", []))),
            ("Reddit Trends", len(insights.get("reddit_trends", []))),
            ("YouTube Signals", len(insights.get("youtube_trends", []))),
            ("Market FAQs", len(insights.get("faqs", []))),
            ("Products Listed", len(insights.get("immersive_products", [])) + len(insights.get("more_products", []))),
            ("Content Sections", len(sections))
        ]

        # Draw structured metric containers
        for idx, (label, val) in enumerate(metrics_data):
            col = idx % 4
            row = idx // 4
            card = tk.Frame(metrics_frame, bg=BG_SECONDARY, highlightbackground=BG_TERTIARY, highlightthickness=1)
            card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            metrics_frame.columnconfigure(col, weight=1)
            
            tk.Label(card, text=str(val), font=("Segoe UI", 16, "bold"), fg=ACCENT_BLUE, bg=BG_SECONDARY).pack(pady=(8, 2))
            tk.Label(card, text=label, font=("Segoe UI", 8), fg=TEXT_MUTED, bg=BG_SECONDARY).pack(pady=(0, 8))

        # People Also Search For Tags
        pas = insights.get("people_also_search_for", [])
        if pas:
            pas_frame = ttk.Frame(container_frame, style='TFrame')
            pas_frame.pack(fill="x", pady=10)
            ttk.Label(pas_frame, text="🔍 People Also Search For", style='Subheader.TLabel').pack(anchor="w", pady=2)
            
            tags_txt = ", ".join(pas)
            tk.Message(pas_frame, text=tags_txt, fg=ACCENT_BLUE, bg=BG_PRIMARY, font=("Consolas", 9), width=700).pack(anchor="w")

        # Refine This Search chips
        refine = insights.get("refine_searches", [])
        if refine:
            ref_frame = ttk.Frame(container_frame, style='TFrame')
            ref_frame.pack(fill="x", pady=10)
            ttk.Label(ref_frame, text="🔖 Refine This Search", style='Subheader.TLabel').pack(anchor="w", pady=2)
            
            chips_frame = None
            valid_idx = 0
            for item in refine:
                if isinstance(item, dict):
                    q = item.get("query", "")
                    l = item.get("link", "")
                    if q and l:
                        if valid_idx % 6 == 0:
                            chips_frame = ttk.Frame(ref_frame, style='TFrame')
                            chips_frame.pack(fill="x", pady=2)
                            
                        lbl = tk.Label(chips_frame, text=f"🔖 {q}", fg=ACCENT_BLUE, bg=BG_SECONDARY, font=("Segoe UI", 8), cursor="hand2")
                        lbl.pack(side="left", padx=4, pady=2)
                        lbl.bind("<Button-1>", lambda e, url=l: webbrowser.open(url))
                        valid_idx += 1

        # Google Shopping Product list
        prod_pop = [p for p in insights.get("immersive_products", []) if isinstance(p, dict)]
        prod_more = [p for p in insights.get("more_products", []) if isinstance(p, dict)]
        all_prods = prod_pop + prod_more
        
        if all_prods:
            prod_frame = ttk.Frame(container_frame, style='TFrame')
            prod_frame.pack(fill="x", pady=15)
            ttk.Label(prod_frame, text="🛒 Surfaced Shopping Products (Google Shopping Grid)", style='Subheader.TLabel').pack(anchor="w", pady=5)
            
            p_grid_frame = ttk.Frame(prod_frame, style='TFrame')
            p_grid_frame.pack(fill="x")
            
            for p_idx, prod in enumerate(all_prods[:8]): # Cap grid display at 8
                p_col = p_idx % 4
                p_row = p_idx // 4
                
                card = tk.Frame(p_grid_frame, bg=BG_SECONDARY, bd=0, highlightbackground=BG_TERTIARY, highlightthickness=1)
                card.grid(row=p_row, column=p_col, padx=4, pady=4, sticky="nsew")
                p_grid_frame.columnconfigure(p_col, weight=1)
                
                # Resolve link or fallback to Google Shopping search
                p_url = prod.get("link") or prod.get("url")
                if not p_url:
                    import urllib.parse
                    p_url = f"https://www.google.com/search?tbm=shop&q={urllib.parse.quote(prod.get('title', ''))}"
                
                def open_link(e=None, url=p_url):
                    try:
                        import webbrowser
                        webbrowser.open(url)
                    except Exception:
                        pass
                
                # Thumbnail Image Container
                img_lbl = tk.Label(card, bg=BG_SECONDARY, height=90, text="🛒", font=("Segoe UI", 16), fg=BG_BORDER, cursor="hand2")
                img_lbl.pack(fill="x", padx=8, pady=(8, 2))
                img_lbl.bind("<Button-1>", open_link)
                
                thumb = prod.get("thumbnail")
                if thumb:
                    self.fetch_and_set_image(thumb, img_lbl)
                
                # Metadata
                title_clean = prod.get("title", "Unknown")[:45] + "..." if len(prod.get("title", "")) > 45 else prod.get("title", "")
                title_lbl = tk.Label(card, text=title_clean, font=("Segoe UI", 9, "bold"), fg=TEXT_MAIN, bg=BG_SECONDARY, anchor="w", justify="left", cursor="hand2")
                title_lbl.pack(fill="x", padx=8, pady=(2, 2))
                title_lbl.bind("<Button-1>", open_link)
                title_lbl.bind("<Enter>", lambda e, lbl=title_lbl: lbl.configure(fg=ACCENT_BLUE))
                title_lbl.bind("<Leave>", lambda e, lbl=title_lbl: lbl.configure(fg=TEXT_MAIN))
                
                price_clean = prod.get("price", "—")
                tk.Label(card, text=price_clean, font=("Segoe UI", 11, "bold"), fg=ACCENT_GREEN, bg=BG_SECONDARY, anchor="w").pack(fill="x", padx=8)
                
                src = prod.get("source", "")
                if src:
                    src_lbl = tk.Label(card, text=f"📦 {src}", font=("Segoe UI", 8), fg=TEXT_MUTED, bg=BG_SECONDARY, anchor="w", cursor="hand2")
                    src_lbl.pack(fill="x", padx=8, pady=(0, 8))
                    src_lbl.bind("<Button-1>", open_link)
                    src_lbl.bind("<Enter>", lambda e, lbl=src_lbl: lbl.configure(fg=ACCENT_BLUE))
                    src_lbl.bind("<Leave>", lambda e, lbl=src_lbl: lbl.configure(fg=TEXT_MUTED))

        # Inline Videos Display
        vids_in = insights.get("inline_videos", [])
        vids_more = insights.get("more_videos", [])
        all_vids = vids_in + vids_more
        
        if all_vids:
            vid_frame = ttk.Frame(container_frame, style='TFrame')
            vid_frame.pack(fill="x", pady=15)
            ttk.Label(vid_frame, text="🎬 Referenced Video Content (SERP / Perspectives)", style='Subheader.TLabel').pack(anchor="w", pady=5)
            
            v_container = ttk.Frame(vid_frame, style='TFrame')
            v_container.pack(fill="x")
            for v_idx, vid in enumerate(all_vids[:6]):
                v_col = v_idx % 3
                v_row = v_idx // 3
                
                card = tk.Frame(v_container, bg=BG_SECONDARY, bd=0, highlightbackground=BG_TERTIARY, highlightthickness=1)
                card.grid(row=v_row, column=v_col, padx=4, pady=4, sticky="nsew")
                v_container.columnconfigure(v_col, weight=1)
                
                title_v = vid.get("title", "Unknown")[:50] + "..." if len(vid.get("title", "")) > 50 else vid.get("title", "")
                lbl_v = tk.Label(card, text=title_v, font=("Segoe UI", 9, "bold"), fg=TEXT_MAIN, bg=BG_SECONDARY, cursor="hand2", anchor="w", justify="left")
                lbl_v.pack(fill="x", padx=8, pady=(8, 2))
                if vid.get("link"):
                    lbl_v.bind("<Button-1>", lambda e, url=vid.get("link"): webbrowser.open(url))
                
                meta_v = " · ".join(filter(None, [vid.get("channel"), vid.get("platform"), vid.get("duration")]))
                tk.Label(card, text=f"📺 {meta_v}", font=("Segoe UI", 8), fg=TEXT_MUTED, bg=BG_SECONDARY, anchor="w").pack(fill="x", padx=8, pady=(0, 8))

        # Google AI Overview Text blocks
        ai_txt = insights.get("ai_overview_text", [])
        ai_ref = insights.get("ai_overview_references", [])
        if ai_txt or ai_ref:
            ai_frame = ttk.Frame(container_frame, style='TFrame')
            ai_frame.pack(fill="x", pady=15)
            ttk.Label(ai_frame, text="🤖 Google AI Overview", style='Subheader.TLabel').pack(anchor="w", pady=5)
            
            for block in ai_txt:
                bk = tk.Frame(ai_frame, bg=BG_SECONDARY, bd=0, highlightbackground="#6366f1", highlightthickness=1)
                bk.pack(fill="x", pady=3)
                tk.Label(bk, text=block, font=("Segoe UI", 9), fg=TEXT_MAIN, bg=BG_SECONDARY, wraplength=700, justify="left", anchor="w").pack(fill="x", padx=10, pady=8)

        # ── Two-Column Split Layout ──────────────────────────────────────────
        two_col_frame = ttk.Frame(container_frame, style='TFrame')
        two_col_frame.pack(fill="both", expand=True, pady=15)
        two_col_frame.columnconfigure(0, weight=2)
        two_col_frame.columnconfigure(1, weight=1)
        
        left_col = ttk.Frame(two_col_frame, style='TFrame')
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        
        right_col = ttk.Frame(two_col_frame, style='TFrame')
        right_col.grid(row=0, column=1, sticky="nsew")

        # 1. Left Column: Generated Article Sections
        content_header = "📝 Blog Article Sections" if data.get("content_type") == "keyword" else "✍️ Generated Page Sections"
        section_frame = ttk.Frame(left_col, style='TFrame')
        section_frame.pack(fill="x")
        ttk.Label(section_frame, text=content_header, style='Subheader.TLabel').pack(anchor="w", pady=5)
        
        for s_idx, sec in enumerate(sections, 1):
            sec_hdr_frame = ttk.Frame(section_frame, style='TFrame')
            sec_hdr_frame.pack(fill="x", pady=(10, 2))
            
            sec_title_lbl = tk.Label(sec_hdr_frame, text=f"## {s_idx}. {sec['heading']}", font=("Segoe UI", 12, "bold"), fg=ACCENT_BLUE, bg=BG_PRIMARY, anchor="w")
            sec_title_lbl.pack(side="left", fill="x", expand=True)
            
            full_sec_text = f"## {sec['heading']}\n\n{sec.get('body', '')}"
            copy_btn = self.create_compact_button(sec_hdr_frame, "📋 Copy", None)
            copy_btn.configure(command=lambda t=full_sec_text, btn=copy_btn: self.copy_to_clipboard(t, btn))
            copy_btn.pack(side="right", padx=5)
            
            # Format custom H3 tags and sentence bullets
            body = sec.get("body", "")
            for line in body.split("\n"):
                line_str = line.strip()
                if not line_str:
                    continue
                if line_str.startswith("### "):
                    tk.Label(section_frame, text=f"▸ {line_str[4:]}", font=("Segoe UI", 10, "bold"), fg=ACCENT_PURPLE, bg=BG_PRIMARY, anchor="w").pack(fill="x", padx=15, pady=(5, 2))
                elif line_str.startswith("- ") or line_str.startswith("• "):
                    bul_txt = line_str[2:].strip()
                    tk.Label(section_frame, text=f"◦ {bul_txt}", font=("Segoe UI", 9), fg=TEXT_MAIN, bg=BG_PRIMARY, wraplength=450, justify="left", anchor="w").pack(fill="x", padx=30, pady=1)
                else:
                    tk.Label(section_frame, text=line_str, font=("Segoe UI", 9), fg=TEXT_MAIN, bg=BG_PRIMARY, wraplength=450, justify="left", anchor="w").pack(fill="x", padx=15, pady=2)
            
            # Divider
            tk.Frame(section_frame, height=1, bg=BG_SECONDARY).pack(fill="x", pady=15)

        # 2. Right Column: Market & SEO Insights tabbed panel
        ttk.Label(right_col, text="🧠 Market & SEO Insights", style='Subheader.TLabel').pack(anchor="w", pady=5)
        
        style = ttk.Style()
        style.configure('TNotebook', background=BG_PRIMARY, borderwidth=0)
        style.configure('TNotebook.Tab', background=BG_SECONDARY, foreground=TEXT_MUTED, borderwidth=1, padding=(8, 4), font=("Segoe UI", 9))
        style.map('TNotebook.Tab', background=[('selected', BG_TERTIARY)], foreground=[('selected', TEXT_MAIN)])
        
        notebook = ttk.Notebook(right_col, style='TNotebook')
        notebook.pack(fill="both", expand=True, pady=5)

        # Add specific SEO insight tabs
        tab_keywords = ttk.Frame(notebook, style='TFrame')
        tab_auto = ttk.Frame(notebook, style='TFrame')
        tab_paa = ttk.Frame(notebook, style='TFrame')
        tab_reddit = ttk.Frame(notebook, style='TFrame')
        tab_youtube = ttk.Frame(notebook, style='TFrame')
        tab_faqs = ttk.Frame(notebook, style='TFrame')
        
        notebook.add(tab_keywords, text="🔑 Keywords")
        notebook.add(tab_auto, text="🔮 Auto")
        notebook.add(tab_paa, text="❓ PAA")
        notebook.add(tab_reddit, text="💬 Reddit")
        notebook.add(tab_youtube, text="▶️ YouTube")
        notebook.add(tab_faqs, text="🙋 FAQs")

        # Tab 1: Keywords List
        kws = insights.get("keywords", [])
        if kws:
            kw_box = tk.Text(tab_keywords, bg=BG_SECONDARY, fg=ACCENT_BLUE, bd=0, font=("Consolas", 9), wrap="word", height=15)
            kw_box.pack(fill="both", expand=True, padx=5, pady=5)
            for kw in kws:
                kw_box.insert("end", f"✨ {kw}\n")
            kw_box.configure(state="disabled")
        else:
            tk.Label(tab_keywords, text="No keywords found.", fg=TEXT_MUTED, bg=BG_PRIMARY, font=("Segoe UI", 9, "italic")).pack(pady=10)

        # Tab 2: Autocomplete Terms
        auto = insights.get("autocomplete_keywords", [])
        if auto:
            auto_box = tk.Text(tab_auto, bg=BG_SECONDARY, fg=ACCENT_BLUE, bd=0, font=("Consolas", 9), wrap="word", height=15)
            auto_box.pack(fill="both", expand=True, padx=5, pady=5)
            for kw in auto:
                auto_box.insert("end", f"🔎 {kw}\n")
            auto_box.configure(state="disabled")
        else:
            tk.Label(tab_auto, text="No autocomplete suggestions.", fg=TEXT_MUTED, bg=BG_PRIMARY, font=("Segoe UI", 9, "italic")).pack(pady=10)

        # Tab 3: People Also Ask (PAA)
        paa = insights.get("people_also_ask", [])
        if paa:
            paa_box = tk.Text(tab_paa, bg=BG_SECONDARY, fg=TEXT_MAIN, bd=0, font=("Segoe UI", 9), wrap="word", height=15)
            paa_box.pack(fill="both", expand=True, padx=5, pady=5)
            for q in paa:
                paa_box.insert("end", f"❓ {q}\n\n")
            paa_box.configure(state="disabled")
        else:
            tk.Label(tab_paa, text="No PAA questions found.", fg=TEXT_MUTED, bg=BG_PRIMARY, font=("Segoe UI", 9, "italic")).pack(pady=10)

        # Tab 4: Reddit discussions
        reddit = insights.get("reddit_trends", [])
        if reddit:
            reddit_box = tk.Text(tab_reddit, bg=BG_SECONDARY, fg=ACCENT_PURPLE, bd=0, font=("Segoe UI", 9), wrap="word", height=15)
            reddit_box.pack(fill="both", expand=True, padx=5, pady=5)
            for r in reddit:
                reddit_box.insert("end", f"💬 {r}\n\n")
            reddit_box.configure(state="disabled")
        else:
            tk.Label(tab_reddit, text="No Reddit trends found.", fg=TEXT_MUTED, bg=BG_PRIMARY, font=("Segoe UI", 9, "italic")).pack(pady=10)

        # Tab 5: YouTube Signal Links
        yt_items = insights.get("youtube_trends", [])
        if yt_items:
            yt_scroll = ScrollableFrame(tab_youtube)
            yt_scroll.pack(fill="both", expand=True)
            for yt in yt_items:
                if isinstance(yt, dict):
                    t_val = yt.get("title", "")
                    u_val = yt.get("url", "")
                    if u_val and t_val:
                        lbl = tk.Label(yt_scroll.scrollable_frame, text=f"▶️ {t_val}", fg=ACCENT_BLUE, bg=BG_PRIMARY, font=("Segoe UI", 9), cursor="hand2", wraplength=220, justify="left", anchor="w")
                        lbl.pack(fill="x", anchor="w", pady=3)
                        lbl.bind("<Button-1>", lambda e, url=u_val: webbrowser.open(url))
                    elif t_val:
                        tk.Label(yt_scroll.scrollable_frame, text=f"▶️ {t_val}", fg=TEXT_MAIN, bg=BG_PRIMARY, font=("Segoe UI", 9), wraplength=220, justify="left", anchor="w").pack(fill="x", anchor="w", pady=3)
                else:
                    tk.Label(yt_scroll.scrollable_frame, text=f"▶️ {yt}", fg=TEXT_MAIN, bg=BG_PRIMARY, font=("Segoe UI", 9), wraplength=220, justify="left", anchor="w").pack(fill="x", anchor="w", pady=3)
        else:
            tk.Label(tab_youtube, text="No YouTube signals found.", fg=TEXT_MUTED, bg=BG_PRIMARY, font=("Segoe UI", 9, "italic")).pack(pady=10)

        # Tab 6: FAQs List
        faqs = insights.get("faqs", [])
        if faqs:
            faqs_box = tk.Text(tab_faqs, bg=BG_SECONDARY, fg=TEXT_MAIN, bd=0, font=("Segoe UI", 9), wrap="word", height=15)
            faqs_box.pack(fill="both", expand=True, padx=5, pady=5)
            for faq in faqs:
                faqs_box.insert("end", f"🙋 {faq}\n\n")
            faqs_box.configure(state="disabled")
        else:
            tk.Label(tab_faqs, text="No FAQs found.", fg=TEXT_MUTED, bg=BG_PRIMARY, font=("Segoe UI", 9, "italic")).pack(pady=10)

    def save_json_dialog(self, data):
        filename = f"{data['name'].replace(' ','_').lower()}_{data['id'][:8]}.json"
        filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")], initialfile=filename)
        if filepath:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Saved", "JSON report successfully exported!")

    def save_csv_dialog(self, data):
        insights = data.get("insights", {})
        csv_rows = []
        for s in data.get("sections", []):
            csv_rows.append({"Category": "Section", "Heading/Type": s["heading"], "Value": s["body"][:100]+"..."})
        for kw in insights.get("keywords", []):
            csv_rows.append({"Category": "Keyword", "Heading/Type": "SEO Keyword", "Value": kw})
        for term in insights.get("people_also_search_for", []):
            csv_rows.append({"Category": "SERP", "Heading/Type": "People Also Search For", "Value": term})
        for q in insights.get("people_also_ask", []):
            csv_rows.append({"Category": "SERP", "Heading/Type": "People Also Ask", "Value": q})

        if not csv_rows:
            messagebox.showwarning("Empty", "No metrics found to export.")
            return

        filename = f"{data['name'].replace(' ','_').lower()}_{data['id'][:8]}.csv"
        filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")], initialfile=filename)
        if filepath:
            df = pd.DataFrame(csv_rows)
            df.to_csv(filepath, index=False, encoding="utf-8")
            messagebox.showinfo("Saved", "Keywords CSV successfully exported!")

    # --- PAGE 2: STRATEGY VAULT ---
    def build_library_page(self):
        page = ttk.Frame(self.viewport, style='TFrame')
        
        # Header
        lbl_frame = ttk.Frame(page, style='TFrame')
        lbl_frame.pack(fill="x", padx=30, pady=20)
        ttk.Label(lbl_frame, text="STRATEGY VAULT", style='Header.TLabel').pack(anchor="w")
        ttk.Label(lbl_frame, text="Browse your portfolio of SEO-optimized articles and research reports.", style='Subtitle.TLabel').pack(anchor="w", pady=(5, 0))

        # Metrics overview counters
        met_frame = ttk.Frame(page, style='TFrame')
        met_frame.pack(fill="x", padx=30, pady=5)
        
        self.lib_total_card = tk.Frame(met_frame, bg=BG_SECONDARY, highlightbackground=BG_TERTIARY, highlightthickness=1)
        self.lib_total_card.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self.lbl_lib_total_val = tk.Label(self.lib_total_card, text="0", font=("Segoe UI", 16, "bold"), fg=ACCENT_BLUE, bg=BG_SECONDARY)
        self.lbl_lib_total_val.pack(pady=(8, 2))
        tk.Label(self.lib_total_card, text="Total Documents", font=("Segoe UI", 8), fg=TEXT_MUTED, bg=BG_SECONDARY).pack(pady=(0, 8))

        self.lib_recent_card = tk.Frame(met_frame, bg=BG_SECONDARY, highlightbackground=BG_TERTIARY, highlightthickness=1)
        self.lib_recent_card.pack(side="left", fill="both", expand=True)
        self.lbl_lib_recent_val = tk.Label(self.lib_recent_card, text="—", font=("Segoe UI", 14, "bold"), fg=ACCENT_BLUE, bg=BG_SECONDARY)
        self.lbl_lib_recent_val.pack(pady=(8, 2))
        tk.Label(self.lib_recent_card, text="Most Recent", font=("Segoe UI", 8), fg=TEXT_MUTED, bg=BG_SECONDARY).pack(pady=(0, 8))

        # Dynamic Combobox Archive Picker
        pick_frame = ttk.Frame(page, style='TFrame')
        pick_frame.pack(fill="x", padx=30, pady=15)
        ttk.Label(pick_frame, text="Select an archive report to analyze:").pack(side="left", padx=(0, 10))
        self.cmb_lib_docs = ttk.Combobox(pick_frame, state="readonly", width=50)
        self.cmb_lib_docs.pack(side="left", fill="x", expand=True, ipady=4)
        self.cmb_lib_docs.bind("<<ComboboxSelected>>", self.handle_lib_doc_select)

        # Core Report table list
        table_frame = ttk.Frame(page, style='TFrame')
        table_frame.pack(fill="x", padx=30, pady=5)
        
        cols = ("Keyword/Title", "Type", "Region", "Created", "Auto-Refresh")
        self.lib_tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=6)
        for c in cols:
            self.lib_tree.heading(c, text=c)
            self.lib_tree.column(c, width=120, anchor="center")
        self.lib_tree.pack(fill="x")
        self.lib_tree.bind("<<TreeviewSelect>>", self.handle_lib_tree_select)

        # Dynamic details view scroll container
        self.lib_scroll = ScrollableFrame(page)
        self.lib_scroll.pack(fill="both", expand=True, padx=30, pady=10)
        self.lib_details_frame = self.lib_scroll.scrollable_frame

        return page

    def load_archive_list(self):
        try:
            self.archive_data = list_all_content_json()
            total = len(self.archive_data)
            self.lbl_lib_total_val.configure(text=str(total))
            if total > 0:
                self.lbl_lib_recent_val.configure(text=self.archive_data[0].get("name", "—"))
            else:
                self.lbl_lib_recent_val.configure(text="—")

            # Pop tree rows
            for row in self.lib_tree.get_children():
                self.lib_tree.delete(row)

            doc_options = []
            for item in self.archive_data:
                cid = item["id"]
                name = item["name"]
                doc_options.append(f"{name} ({cid[:8]})")
                
                self.lib_tree.insert("", "end", iid=cid, values=(
                    name,
                    item.get("content_type", "—").capitalize(),
                    item.get("country", "—"),
                    item.get("created_at", "")[:10],
                    item.get("refresh_interval", "—").capitalize()
                ))

            self.cmb_lib_docs.configure(values=doc_options)
            if doc_options:
                self.cmb_lib_docs.current(0)
                
        except Exception as e:
            pass

    def handle_lib_doc_select(self, event=None):
        idx = self.cmb_lib_docs.current()
        if idx >= 0:
            doc = self.archive_data[idx]
            cid = doc["id"]
            self.load_detailed_doc(cid)

    def handle_lib_tree_select(self, event=None):
        selected = self.lib_tree.selection()
        if selected:
            cid = selected[0]
            self.load_detailed_doc(cid)

    def load_detailed_doc(self, cid):
        # Read from core Direct JSON library
        record = load_content_json(cid)
        if not record:
            messagebox.showerror("Not Found", "Failed to retrieve local file.")
            return
            
        saved = record.get("insights", {})
        loaded = _load_insights(saved)
        
        # Hydrate values
        full_content = {
            "id": record["id"],
            "name": record["name"],
            "content_type": record["content_type"],
            "country": record["country"],
            "sections": record["sections"],
            "insights": loaded,
            "sources_used": record.get("sources_used", []),
            "source_urls": record.get("source_urls", []),
            "created_at": record["created_at"],
            "refresh_interval": record["refresh_interval"],
            "custom_interval_hours": record.get("custom_interval_hours"),
            "next_refresh_at": record.get("next_refresh_at")
        }
        
        self.render_generated_results(full_content, self.lib_details_frame)



    # --- PAGE 4: RESEARCH HUB ---
    def build_research_page(self):
        page = ttk.Frame(self.viewport, style='TFrame')
        
        # Header
        lbl_frame = ttk.Frame(page, style='TFrame')
        lbl_frame.pack(fill="x", padx=30, pady=20)
        ttk.Label(lbl_frame, text="RESEARCH HUB", style='Header.TLabel').pack(anchor="w")
        ttk.Label(lbl_frame, text="Full DataForSEO-powered SEO intelligence — keywords, rankings, content ideas, site analysis & audits.", style='Subtitle.TLabel').pack(anchor="w", pady=(5, 0))

        # Inputs Bar
        form_frame = ttk.Frame(page, style='TFrame')
        form_frame.pack(fill="x", padx=30, pady=10)
        
        ttk.Label(form_frame, text="Target Keyword").grid(row=0, column=0, padx=5, sticky="w")
        self.ent_dr_keyword = CanvasEntry(form_frame, placeholder="e.g., sustainable fashion trends")
        self.ent_dr_keyword.grid(row=1, column=0, padx=5, pady=2, sticky="ew")
        
        ttk.Label(form_frame, text="Target Domain / URL").grid(row=0, column=1, padx=5, sticky="w")
        self.ent_dr_url = CanvasEntry(form_frame, placeholder="e.g., brandname.com")
        self.ent_dr_url.grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(form_frame, text="Country Target").grid(row=0, column=2, padx=5, sticky="w")
        self.cmb_dr_country = CanvasDropdown(form_frame, values=list(ah.COUNTRY_CODES.keys()), initial_index=0)
        self.cmb_dr_country.grid(row=1, column=2, padx=5, pady=2, sticky="ew")

        form_frame.columnconfigure(0, weight=2)
        form_frame.columnconfigure(1, weight=2)
        form_frame.columnconfigure(2, weight=1)

        # Tabbed Console Frames
        tab_btn_frame = ttk.Frame(page, style='TFrame')
        tab_btn_frame.pack(fill="x", padx=30, pady=10)
        
        self.dr_tab = "kw"
        self.btn_dr_kw = self.create_modern_button(tab_btn_frame, "🔍 Keyword Explorer", lambda: self.switch_dr_tab("kw"), primary=True)
        self.btn_dr_kw.pack(side="left", padx=2)
        self.btn_dr_rank = self.create_modern_button(tab_btn_frame, "📈 Rank Tracker", lambda: self.switch_dr_tab("rank"))
        self.btn_dr_rank.pack(side="left", padx=2)
        self.btn_dr_content = self.create_modern_button(tab_btn_frame, "📝 Content Explorer", lambda: self.switch_dr_tab("content"))
        self.btn_dr_content.pack(side="left", padx=2)
        self.btn_dr_site = self.create_modern_button(tab_btn_frame, "🌐 Site Explorer", lambda: self.switch_dr_tab("site"))
        self.btn_dr_site.pack(side="left", padx=2)

        # Viewport Panels
        self.dr_scroll = ScrollableFrame(page)
        self.dr_scroll.pack(fill="both", expand=True, padx=30, pady=10)
        self.dr_container = self.dr_scroll.scrollable_frame

        # Loading Spinner block
        self.dr_loader = ttk.Frame(self.dr_container, style='TFrame')
        self.dr_loader_lbl = ttk.Label(self.dr_loader, text="🔬 Querying Live SEO Databases...", style='Subheader.TLabel')
        self.dr_loader_lbl.pack(pady=10)
        self.dr_progress = ttk.Progressbar(self.dr_loader, mode='indeterminate', length=200)
        self.dr_progress.pack(pady=5)

        # Viewport Containers
        self.dr_sub_frames = {}
        for key in ["kw", "rank", "content", "site"]:
            self.dr_sub_frames[key] = ttk.Frame(self.dr_container, style='TFrame')

        # Initialize buttons and instruction placeholders inside each container tab
        self.render_dr_kw_results({})
        self.render_dr_rank_results(None)
        self.render_dr_content_results(None)
        self.render_dr_site_results({})

        self.switch_dr_tab("kw")
        return page

    def switch_dr_tab(self, tab_key):
        self.dr_tab = tab_key
        buttons = [
            ("kw", self.btn_dr_kw),
            ("rank", self.btn_dr_rank),
            ("content", self.btn_dr_content),
            ("site", self.btn_dr_site)
        ]
        
        for k, btn in buttons:
            if k == tab_key:
                btn.configure(bg=ACCENT_CYAN, fg=BG_PRIMARY)
                # Rebind hover states for selected tab button
                btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=ACCENT_BLUE, fg=BG_PRIMARY))
                btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=ACCENT_CYAN, fg=BG_PRIMARY))
                self.dr_sub_frames[k].pack(fill="both", side="top")
            else:
                btn.configure(bg=BG_SECONDARY, fg=TEXT_MAIN)
                # Rebind hover states for unselected tab buttons
                btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=BG_TERTIARY, fg=ACCENT_CYAN))
                btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=BG_SECONDARY, fg=TEXT_MAIN))
                self.dr_sub_frames[k].pack_forget()

    def show_dr_loading(self, show=True):
        if show:
            for k in self.dr_sub_frames:
                self.dr_sub_frames[k].pack_forget()
            self.dr_loader.pack(fill="x", pady=40)
            self.dr_progress.start(10)
        else:
            self.dr_progress.stop()
            self.dr_loader.pack_forget()
            self.dr_sub_frames[self.dr_tab].pack(fill="both", side="top")

    # 1. KEYWORD EXPLORER METRICS RENDERERS
    def handle_dr_kw_explore(self):
        kw = self.ent_dr_keyword.entry.get().strip()
        country = self.cmb_dr_country.get()
        url = self.ent_dr_url.entry.get().strip()

        if not kw:
            messagebox.showwarning("Missing Keyword", "Please enter a target keyword.")
            return

        self.show_dr_loading(True)

        def query_database():
            overview = ah.keyword_overview(kw, country)
            ideas = ah.keyword_ideas(kw, country, limit=100)
            also = ah.keyword_also_rank_for(kw, country, limit=50)
            suggest = ah.keyword_search_suggestions(kw, country, limit=50)
            
            # Optional Keyword Planner Check
            planner_ideas, planner_err = [], None
            if is_google_ads_planner_configured():
                planner_ideas, planner_err = fetch_keyword_planner_ideas(kw, country, url or None, limit=100)
            else:
                planner_err = "Google Ads credentials not configured in .env file (missing variables)."

            return {
                "overview": overview,
                "ideas": ideas,
                "also": also,
                "suggest": suggest,
                "planner": {"ideas": planner_ideas, "error": planner_err}
            }

        def on_success(res):
            self.show_dr_loading(False)
            self.render_dr_kw_results(res)

        self.run_threaded_task(query_database, success_cb=on_success)

    def render_dr_kw_results(self, res):
        frame = self.dr_sub_frames["kw"]
        for child in frame.winfo_children():
            child.destroy()

        self.create_modern_button(frame, "🚀 Fetch Keyword Ideas", self.handle_dr_kw_explore, primary=True).pack(anchor="w", pady=10)

        if not res:
            ttk.Label(frame, text="Enter a keyword and URL above, then click to begin exploration.", style='Subtitle.TLabel').pack(pady=20)
            return

        # Overview Stats
        ov = res.get("overview", {})
        if ov and "error" not in ov:
            ttk.Label(frame, text="📊 Keyword Search Overview", style='Subheader.TLabel').pack(anchor="w", pady=5)
            
            stat_frame = ttk.Frame(frame, style='TFrame')
            stat_frame.pack(fill="x", pady=5)
            
            metrics = [
                ("Search Volume", ov.get("volume", "—")),
                ("Keyword Difficulty", ov.get("difficulty", "—")),
                ("Average CPC ($)", ov.get("cpc", "—")),
                ("Global Volume", ov.get("global_volume", "—"))
            ]
            for s_idx, (lbl, val) in enumerate(metrics):
                card = tk.Frame(stat_frame, bg=BG_SECONDARY, highlightbackground=BG_TERTIARY, highlightthickness=1)
                card.pack(side="left", fill="both", expand=True, padx=4)
                tk.Label(card, text=str(val), font=("Segoe UI", 14, "bold"), fg=ACCENT_BLUE, bg=BG_SECONDARY).pack(pady=(8, 2))
                tk.Label(card, text=lbl, font=("Segoe UI", 8), fg=TEXT_MUTED, bg=BG_SECONDARY).pack(pady=(0, 8))

        # Consolidated Table display
        ttk.Label(frame, text="💡 Consolidated Keyword Ideas", style='Subheader.TLabel').pack(anchor="w", pady=(15, 5))
        
        # Normalization
        def normalize(items, src_name):
            out = []
            for item in items:
                if isinstance(item, dict):
                    vol = item.get("volume", "—")
                    cpc = f"{float(item['cpc']):.2f}" if isinstance(item.get("cpc"), (int, float)) and item["cpc"] > 0 else "—"
                    out.append({
                        "Keyword": item.get("keyword", ""),
                        "Volume": vol if vol not in (None, "", 0) else "—",
                        "KD": item.get("difficulty", "—"),
                        "CPC ($)": cpc,
                        "Source": src_name
                    })
            return out

        all_kws = (
            normalize(res.get("ideas", []), "Phrase Match") +
            normalize(res.get("also", []), "Also Rank For") +
            normalize(res.get("suggest", []), "Suggestions")
        )
        
        planner_data = res.get("planner", {})
        planner_err = planner_data.get("error")
        if planner_err:
            print(f"⚠️ Google Ads API Notice: {planner_err}")
            log_google_ads_error(planner_err)
        if planner_data.get("ideas"):
            all_kws += normalize(planner_data["ideas"], "Google Ads")

        # Deduplication
        merged = []
        seen = {}
        for row in all_kws:
            kw_key = row["Keyword"].lower().strip()
            if not kw_key:
                continue
            if kw_key not in seen:
                seen[kw_key] = len(merged)
                merged.append(row)
            else:
                cur = merged[seen[kw_key]]
                if row["Source"] not in cur["Source"]:
                    cur["Source"] += f" · {row['Source']}"

        self.dr_all_keywords = merged
        
        if merged:
            table_lbl = ttk.Label(frame, text=f"Surfaced {len(merged)} related terms:")
            table_lbl.pack(anchor="w")

            t_frame = ttk.Frame(frame, style='TFrame')
            t_frame.pack(fill="x", pady=5)
            
            tree_cols = ("Keyword", "Volume", "KD", "CPC ($)", "Source")
            tree = ttk.Treeview(t_frame, columns=tree_cols, show="headings", height=8)
            for c in tree_cols:
                tree.heading(c, text=c)
                tree.column(c, width=110, anchor="center")
            tree.pack(fill="x")
            
            for row in merged:
                tree.insert("", "end", values=(row["Keyword"], row["Volume"], row["KD"], row["CPC ($)"], row["Source"]))
                
            self.create_modern_button(frame, "📥 Export CSV Table", lambda: self.save_raw_csv_dialog(merged), primary=True).pack(pady=10)
        else:
            ttk.Label(frame, text="No keyword ideas found.", style='Subtitle.TLabel').pack(pady=10)

    def save_raw_csv_dialog(self, rows):
        filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if filepath:
            pd.DataFrame(rows).to_csv(filepath, index=False)
            messagebox.showinfo("Exported", "Data successfully exported!")

    # 2. RANK TRACKER
    def handle_dr_rank_track(self):
        url = self.ent_dr_url.entry.get().strip()
        country = self.cmb_dr_country.get()
        keyword = self.ent_dr_keyword.entry.get().strip()

        if not url:
            messagebox.showwarning("Domain Missing", "Please enter a target domain URL.")
            return

        self.show_dr_loading(True)

        def query():
            kws = [keyword] if keyword else []
            return ah.rank_tracker_positions(url, country, kws, limit=100)

        def on_success(res):
            self.show_dr_loading(False)
            self.render_dr_rank_results(res)

        self.run_threaded_task(query, success_cb=on_success)

    def render_dr_rank_results(self, res):
        frame = self.dr_sub_frames["rank"]
        for child in frame.winfo_children():
            child.destroy()

        self.create_modern_button(frame, "🚀 Track Domain Rankings", self.handle_dr_rank_track, primary=True).pack(anchor="w", pady=10)

        if res is None:
            ttk.Label(frame, text="Enter a domain URL and keyword above, then click to track rankings.", style='Subtitle.TLabel').pack(pady=20)
            return

        if res:
            t_frame = ttk.Frame(frame, style='TFrame')
            t_frame.pack(fill="x", pady=5)
            
            tree_cols = ("Keyword", "Rank Pos", "Organic Traffic", "Vol", "KD", "CPC")
            tree = ttk.Treeview(t_frame, columns=tree_cols, show="headings", height=8)
            for c in tree_cols:
                tree.heading(c, text=c)
                tree.column(c, width=100, anchor="center")
            tree.pack(fill="x")
            
            for row in res:
                tree.insert("", "end", values=(
                    row.get("keyword", ""),
                    row.get("position", "—"),
                    row.get("traffic", "—"),
                    row.get("volume", "—"),
                    row.get("difficulty", "—"),
                    row.get("cpc", "—")
                ))
        else:
            ttk.Label(frame, text="No ranking data identified.", style='Subtitle.TLabel').pack(pady=10)

    # 3. CONTENT EXPLORER
    def handle_dr_content_explore(self):
        kw = self.ent_dr_keyword.entry.get().strip()
        if not kw:
            messagebox.showwarning("Missing Keyword", "Please enter a target keyword.")
            return

        self.show_dr_loading(True)

        def query():
            return ah.content_explorer(kw, limit=20)

        def on_success(res):
            self.show_dr_loading(False)
            self.render_dr_content_results(res)

        self.run_threaded_task(query, success_cb=on_success)

    def render_dr_content_results(self, res):
        frame = self.dr_sub_frames["content"]
        for child in frame.winfo_children():
            child.destroy()

        self.create_modern_button(frame, "🚀 Find Viral Content", self.handle_dr_content_explore, primary=True).pack(anchor="w", pady=10)

        if res is None:
            ttk.Label(frame, text="Enter a target keyword above, then click to find viral content.", style='Subtitle.TLabel').pack(pady=20)
            return

        if res:
            for idx, art in enumerate(res, 1):
                card = tk.Frame(frame, bg=BG_SECONDARY, bd=0, highlightbackground=BG_TERTIARY, highlightthickness=1)
                card.pack(fill="x", pady=5)
                
                title = art.get("title", "")[:80] + "..." if len(art.get("title", "")) > 80 else art.get("title", "")
                lbl = tk.Label(card, text=f"#{idx} — {title}", font=("Segoe UI", 10, "bold"), fg=ACCENT_BLUE, bg=BG_SECONDARY, cursor="hand2", anchor="w")
                lbl.pack(fill="x", padx=15, pady=(8, 2))
                if art.get("url"):
                    lbl.bind("<Button-1>", lambda e, url=art["url"]: webbrowser.open(url))
                
                meta_frame = ttk.Frame(card, style='Secondary.TFrame')
                meta_frame.pack(fill="x", padx=15, pady=(2, 8))
                
                stats_str = f"Traffic: {art.get('traffic', '—')}  |  FB Shares: {art.get('facebook_shares', '—')}  |  Tweets: {art.get('twitter_shares', '—')}  |  Ref Domains: {art.get('referring_domains', '—')}"
                ttk.Label(meta_frame, text=stats_str, style='SecondaryMuted.TLabel').pack(anchor="w")
        else:
            ttk.Label(frame, text="No viral articles found.", style='Subtitle.TLabel').pack(pady=10)

    # 4. SITE ORGANIC EXPLORER
    def handle_dr_site_explore(self):
        url = self.ent_dr_url.entry.get().strip()
        country = self.cmb_dr_country.get()
        if not url:
            messagebox.showwarning("Domain Missing", "Please enter a target domain URL.")
            return

        self.show_dr_loading(True)

        def query():
            overview = ah.site_explorer_overview(url, country)
            org_kws = ah.site_explorer_organic_keywords(url, country, 50)
            return {"overview": overview, "kws": org_kws}

        def on_success(res):
            self.show_dr_loading(False)
            self.render_dr_site_results(res)

        self.run_threaded_task(query, success_cb=on_success)

    def render_dr_site_results(self, res):
        frame = self.dr_sub_frames["site"]
        for child in frame.winfo_children():
            child.destroy()

        self.create_modern_button(frame, "🚀 Analyze Site Profile", self.handle_dr_site_explore, primary=True).pack(anchor="w", pady=10)

        if not res:
            ttk.Label(frame, text="Enter a target domain URL above, then click to analyze site profile.", style='Subtitle.TLabel').pack(pady=20)
            return

        ov = res.get("overview", {})
        if ov and "error" not in ov:
            ttk.Label(frame, text="📊 Organic Domain Profile Overview", style='Subheader.TLabel').pack(anchor="w", pady=5)
            
            sc_frame = ttk.Frame(frame, style='TFrame')
            sc_frame.pack(fill="x", pady=5)
            
            metrics = [
                ("Est Organic Traffic", ov.get("org_traffic", "—")),
                ("Organic Keywords", ov.get("org_keywords", "—"))
            ]
            for s_idx, (lbl, val) in enumerate(metrics):
                card = tk.Frame(sc_frame, bg=BG_SECONDARY, highlightbackground=BG_TERTIARY, highlightthickness=1)
                card.pack(side="left", fill="both", expand=True, padx=4)
                tk.Label(card, text=str(val), font=("Segoe UI", 14, "bold"), fg=ACCENT_BLUE, bg=BG_SECONDARY).pack(pady=(8, 2))
                tk.Label(card, text=lbl, font=("Segoe UI", 8), fg=TEXT_MUTED, bg=BG_SECONDARY).pack(pady=(0, 8))

        kws = res.get("kws", [])
        if kws:
            ttk.Label(frame, text="🔑 Ranking Keywords Distribution (Top 50)", style='Subheader.TLabel').pack(anchor="w", pady=(15, 5))
            
            t_frame = ttk.Frame(frame, style='TFrame')
            t_frame.pack(fill="x")
            
            tree_cols = ("Keyword", "Position", "Traffic", "Vol", "KD", "CPC")
            tree = ttk.Treeview(t_frame, columns=tree_cols, show="headings", height=8)
            for c in tree_cols:
                tree.heading(c, text=c)
                tree.column(c, width=100, anchor="center")
            tree.pack(fill="x")
            
            for row in kws:
                tree.insert("", "end", values=(
                    row.get("keyword", ""),
                    row.get("position", "—"),
                    row.get("traffic", "—"),
                    row.get("volume", "—"),
                    row.get("difficulty", "—"),
                    row.get("cpc", "—")
                ))
        else:
            ttk.Label(frame, text="No organic keywords profile.", style='Subtitle.TLabel').pack(pady=10)

    # --- PAGE 5: COMPETITOR INSIGHTS ---
    def build_competitors_page(self):
        page = ttk.Frame(self.viewport, style='TFrame')
        
        # Header
        lbl_frame = ttk.Frame(page, style='TFrame')
        lbl_frame.pack(fill="x", padx=30, pady=20)
        ttk.Label(lbl_frame, text="COMPETITOR INSIGHTS", style='Header.TLabel').pack(anchor="w")
        ttk.Label(lbl_frame, text="Analyze competitor URLs using DataForSEO, SERP & OpenAI to identify content gaps and strategic opportunities.", style='Subtitle.TLabel').pack(anchor="w", pady=(5, 0))

        # Split Configuration Layout
        self.ca_scroll = ScrollableFrame(page)
        self.ca_scroll.pack(fill="both", expand=True, padx=30, pady=10)
        
        container = self.ca_scroll.scrollable_frame
        
        # Configuration Form
        form_frame = ttk.Frame(container, style='TFrame')
        form_frame.pack(fill="x", side="top")
        
        ttk.Label(form_frame, text="Target Keyword").pack(anchor="w", pady=(10, 2))
        self.ent_ca_kw = CanvasEntry(form_frame, placeholder="e.g., sustainable fashion trends")
        self.ent_ca_kw.pack(fill="x", pady=2)

        ttk.Label(form_frame, text="Your Domain / URL (optional)").pack(anchor="w", pady=(10, 2))
        self.ent_ca_our = CanvasEntry(form_frame, placeholder="e.g., yourdomain.com")
        self.ent_ca_our.pack(fill="x", pady=2)

        ttk.Label(form_frame, text="Target Country Search").pack(anchor="w", pady=(10, 2))
        self.cmb_ca_country = CanvasDropdown(form_frame, values=list(ah.COUNTRY_CODES.keys()), initial_index=0)
        self.cmb_ca_country.pack(fill="x", pady=2)

        ttk.Label(form_frame, text="Competitor URLs (One per line, max 5)").pack(anchor="w", pady=(10, 2))
        
        self.ca_txt_border = tk.Frame(form_frame, bg=BG_BORDER, padx=1, pady=1)
        self.ca_txt_border.pack(fill="x", pady=2)
        self.txt_ca_comps = tk.Text(self.ca_txt_border, bg=BG_CONTAINER, fg=TEXT_MAIN, bd=0, insertbackground=TEXT_MAIN, height=5, font=("Segoe UI", 10))
        self.txt_ca_comps.pack(fill="x", expand=True, padx=5, pady=5)

        self.btn_ca_run = self.create_modern_button(form_frame, "🏁 Analyze Competitors", self.handle_ca_run, primary=True)
        self.btn_ca_run.pack(fill="x", pady=20)

        # Loading Progress
        self.ca_status_frame = ttk.Frame(container, style='TFrame')
        self.ca_status_lbl = ttk.Label(self.ca_status_frame, text="🏁 Fetching competitors & scraping outlines...", style='Subheader.TLabel')
        self.ca_status_lbl.pack(pady=10)
        self.ca_progress = ttk.Progressbar(self.ca_status_frame, mode='indeterminate', length=250)
        self.ca_progress.pack(pady=5)

        # Results Tab Control Viewport
        self.ca_results_container = ttk.Frame(container, style='TFrame')

        return page

    def show_ca_loading(self, show=True):
        if show:
            self.ca_status_frame.pack(fill="x", pady=40)
            self.ca_progress.start(10)
            self.ca_results_container.pack_forget()
        else:
            self.ca_progress.stop()
            self.ca_status_frame.pack_forget()
            self.ca_results_container.pack(fill="x", side="top")

    def handle_ca_run(self):
        kw = self.ent_ca_kw.entry.get().strip()
        our_url = self.ent_ca_our.entry.get().strip()
        country = self.cmb_ca_country.get()
        raw_comps = self.txt_ca_comps.get("1.0", tk.END).strip().split("\n")
        comps = [u.strip() for u in raw_comps if u.strip().startswith("http")]

        if not kw:
            messagebox.showwarning("Keyword Missing", "Please enter target keyword.")
            return

        self.show_ca_loading(True)

        def run_analysis():
            from openai import OpenAI
            stopwords = {
                "the", "and", "for", "with", "that", "from", "your", "best", "top", "vs",
                "you", "are", "how", "what", "why", "when", "where", "about", "this", "these",
                "those", "into", "over", "under", "near", "guide", "review", "reviews", "buy"
            }

            def _domain(url):
                try:
                    host = urlparse(url).hostname or ""
                    return host[4:] if host.startswith("www.") else host
                except:
                    return ""

            def _tokenize(text):
                toks = re.findall(r"[a-z0-9]+", (text or "").lower())
                return {t for t in toks if len(t) > 2 and t not in stopwords}

            def _score(text, keyword):
                kw_t = _tokenize(keyword)
                tx_t = _tokenize(text)
                return round(len(kw_t.intersection(tx_t)) / max(1, len(kw_t)), 3) if kw_t and tx_t else 0.0

            # 1. Fetch live organic SERP for competitor candidate prioritization
            serp_results = []
            try:
                serp_key = os.getenv("SERP_API_KEY", "")
                cc = ah._country_code(country)
                r = requests.get("https://serpapi.com/search", params={
                    "q": kw, "api_key": serp_key, "gl": cc, "hl": "en", "num": 10
                }, timeout=15)
                if r.status_code == 200:
                    serp_results = r.json().get("organic_results", [])
            except Exception as e:
                pass

            # Prioritization logic
            serp_c = []
            for item in serp_results[:10]:
                link = item.get("link", "")
                if link:
                    serp_c.append({
                        "url": link, "domain": _domain(link),
                        "score": _score(f"{item.get('title','')} {item.get('snippet','')}", kw),
                        "source": "serp"
                    })

            input_c = [{"url": u, "domain": _domain(u), "score": _score(u, kw), "source": "input"} for u in comps]
            
            serp_domains = {c["domain"] for c in serp_c if c["domain"]}
            selected = []
            seen = set()

            for c in input_c:
                if c["url"] not in seen:
                    if c["domain"] in serp_domains or c["score"] >= 0.2:
                        selected.append(c)
                        seen.add(c["url"])

            for c in sorted(serp_c, key=lambda x: x["score"], reverse=True):
                if len(selected) >= 5:
                    break
                if c["url"] not in seen:
                    selected.append(c)
                    seen.add(c["url"])

            for c in input_c:
                if len(selected) >= 5:
                    break
                if c["url"] not in seen:
                    selected.append(c)
                    seen.add(c["url"])

            comp_urls = [s["url"] for s in selected[:5]]
            relevance_notes = [{"url": s["url"], "source": s["source"], "intent_score": s["score"]} for s in selected[:5]]

            # 2. DataForSEO metrics
            comp_metrics = []
            if comp_urls:
                comp_metrics = ah.competitor_overview_batch(comp_urls, country)

            # 3. Scrape heading structures
            def _scrape(url):
                try:
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36..."}
                    resp = requests.get(url, timeout=8, headers=headers)
                    soup = BeautifulSoup(resp.text, "html.parser")
                    
                    headings = []
                    for t in soup.find_all(["h2", "h3"]):
                        txt = t.get_text(strip=True)
                        if txt:
                            headings.append({"tag": t.name, "text": txt})
                    
                    h2_list = [h["text"] for h in headings if h["tag"] == "h2"]
                    h3_list = [h["text"] for h in headings if h["tag"] == "h3"]
                    title = soup.title.string.strip() if soup.title else ""
                    
                    # Meta description or fallback snippet
                    desc_tag = soup.find("meta", attrs={"name": "description"})
                    desc = desc_tag.get("content", "").strip() if desc_tag else ""
                    if not desc:
                        p_tags = [p.get_text(strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]
                        if p_tags:
                            desc = p_tags[0]
                            if len(desc) > 300:
                                desc = desc[:300] + "..."
                                
                    if not title and not h2_list and not h3_list:
                        return {"url": url, "error": "This page blocked our automated scraper."}
                    return {
                        "url": url,
                        "title": title,
                        "h2": h2_list,
                        "h3": h3_list,
                        "headings": headings,
                        "description": desc
                    }
                except Exception as e:
                    return {"url": url, "error": str(e)}

            comp_content = [_scrape(curl) for curl in comp_urls]

            # 4. OpenAI Gap Analysis
            ai_gaps, ai_sug = [], []
            try:
                own_content = _scrape(our_url) if our_url else {}
                own_h2_h3 = (own_content.get("h2", []) + own_content.get("h3", [])) if own_content else []
                own_heading_set = {h.lower().strip() for h in own_h2_h3 if h}

                all_h = []
                for cc_i in comp_content:
                    all_h.extend(cc_i.get("h2", []) + cc_i.get("h3", []))
                
                selected_headings = list(dict.fromkeys(all_h))[:100]
                h_str = "\n".join(f"- {h}" for h in selected_headings)
                serp_str = "\n".join(f"- {r.get('title','')} — {r.get('snippet','')[:100]}" for r in serp_results[:8])
                own_str = "\n".join(f"- {h}" for h in own_h2_h3[:80]) if own_h2_h3 else "- Not provided"

                gap_prompt = (
                    f"You are an expert SEO content strategist.\n"
                    f"Target keyword: \"{kw}\" | Country: {country}\n\n"
                    f"SERP results:\n{serp_str}\n\n"
                    f"Competitor headings (H2/H3):\n{h_str}\n\n"
                    f"Our headings (H2/H3):\n{own_str}\n\n"
                    f"Identify 8 CONTENT GAPS: subtopics competitors cover that we miss.\n"
                    f"Provide 8 ACTIONABLE SUGGESTIONS to outrank competitors.\n\n"
                    f"Return ONLY valid JSON:\n"
                    f'{{"content_gaps":[...],"suggestions":[]}}'
                )

                oai = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
                completion = oai.chat.completions.create(
                    model="gpt-4o-mini", max_tokens=1000,
                    messages=[
                        {"role": "system", "content": "Expert SEO strategist. Respond only with JSON."},
                        {"role": "user", "content": gap_prompt}
                    ]
                )
                raw_gap = completion.choices[0].message.content.strip().replace("```json","").replace("```","").strip()
                parsed = json.loads(raw_gap)
                ai_gaps = parsed.get("content_gaps", [])
                ai_sug = parsed.get("suggestions", [])
                if own_heading_set:
                    ai_gaps = [g for g in ai_gaps if g.lower().strip() not in own_heading_set]
            except Exception as e:
                pass

            return {
                "serp": serp_results, "ahrefs": comp_metrics,
                "content": comp_content, "gaps": ai_gaps, "sug": ai_sug,
                "kw": kw, "country": country, "relevance_notes": relevance_notes
            }

        def on_success(res):
            self.show_ca_loading(False)
            self.render_ca_results(res)

        self.run_threaded_task(run_analysis, success_cb=on_success)

    def render_ca_results(self, res):
        frame = self.ca_results_container
        for child in frame.winfo_children():
            child.destroy()

        ttk.Label(frame, text=f"📊 Analysis Results: {res['kw']} ({res['country']})", style='Header.TLabel').pack(anchor="w", pady=10)

        # Tabs Layout
        btn_frame = ttk.Frame(frame, style='TFrame')
        btn_frame.pack(fill="x", pady=5)
        
        ca_sub_frames = {}
        for key in ["serp", "metrics", "content", "gaps", "sug"]:
            ca_sub_frames[key] = ttk.Frame(frame, style='TFrame')

        def switch_ca_sub_tab(tab_key):
            for k, tab_btn in ca_btns.items():
                if k == tab_key:
                    tab_btn.configure(bg=ACCENT_CYAN, fg=BG_PRIMARY)
                    ca_sub_frames[k].pack(fill="x", expand=True)
                else:
                    tab_btn.configure(bg=BG_SECONDARY, fg=TEXT_MAIN)
                    ca_sub_frames[k].pack_forget()

        ca_btns = {}
        ca_btns["serp"] = self.create_modern_button(btn_frame, "🔎 SERP Overview", lambda: switch_ca_sub_tab("serp"), primary=True)
        ca_btns["serp"].pack(side="left", padx=2)
        
        ca_btns["metrics"] = self.create_modern_button(btn_frame, "🔗 DataForSEO Metrics", lambda: switch_ca_sub_tab("metrics"))
        ca_btns["metrics"].pack(side="left", padx=2)
        
        ca_btns["content"] = self.create_modern_button(btn_frame, "🕸️ Page Content", lambda: switch_ca_sub_tab("content"))
        ca_btns["content"].pack(side="left", padx=2)
        
        ca_btns["gaps"] = self.create_modern_button(btn_frame, "🕳️ Content Gaps", lambda: switch_ca_sub_tab("gaps"))
        ca_btns["gaps"].pack(side="left", padx=2)
        
        ca_btns["sug"] = self.create_modern_button(btn_frame, "💡 AI Suggestions", lambda: switch_ca_sub_tab("sug"))
        ca_btns["sug"].pack(side="left", padx=2)

        # 1. SERP OVERVIEW
        serp = res.get("serp", [])
        if serp:
            s_tree_cols = ("Pos", "Title", "URL")
            s_tree = ttk.Treeview(ca_sub_frames["serp"], columns=s_tree_cols, show="headings", height=8)
            for c in s_tree_cols:
                s_tree.heading(c, text=c)
                s_tree.column(c, width=120, anchor="center")
            s_tree.pack(fill="x", pady=5)
            for r in serp:
                s_tree.insert("", "end", values=(r.get("position", "—"), r.get("title", ""), r.get("link", "")))

        # 2. METRICS
        ah_d = res.get("ahrefs", [])
        if ah_d:
            m_tree_cols = ("URL", "Domain Rating", "Org Traffic", "Backlinks", "Ref Domains", "Org Keywords")
            m_tree = ttk.Treeview(ca_sub_frames["metrics"], columns=m_tree_cols, show="headings", height=8)
            for c in m_tree_cols:
                m_tree.heading(c, text=c)
                m_tree.column(c, width=110, anchor="center")
            m_tree.pack(fill="x", pady=5)
            for d in ah_d:
                m_tree.insert("", "end", values=(
                    d.get("url", ""), d.get("domain_rating", "—"),
                    d.get("organic_traffic", "—"), d.get("backlinks", "—"),
                    d.get("referring_domains", "—"), d.get("organic_keywords", "—")
                ))

        # 3. CONTENT STRUCTURES
        for cc_i in res.get("content", []):
            url = cc_i.get("url", "")
            err = cc_i.get("error", "")
            title = cc_i.get("title", "")
            description = cc_i.get("description", "")
            headings = cc_i.get("headings", [])
            
            card = tk.Frame(ca_sub_frames["content"], bg=BG_SECONDARY, highlightbackground=BG_TERTIARY, highlightthickness=1)
            card.pack(fill="x", pady=5)
            
            # Header Frame
            header_frame = tk.Frame(card, bg=BG_SECONDARY, cursor="hand2")
            header_frame.pack(fill="x", ipady=4)
            
            # Left side title/url info
            info_frame = tk.Frame(header_frame, bg=BG_SECONDARY)
            info_frame.pack(side="left", fill="both", expand=True, padx=15, pady=6)
            
            lbl_title = tk.Label(info_frame, text=title or "Untitled Page", font=("Segoe UI", 9, "bold"), fg=TEXT_MAIN, bg=BG_SECONDARY, anchor="w")
            lbl_title.pack(fill="x")
            
            lbl_url = tk.Label(info_frame, text=url, font=("Segoe UI", 8), fg=ACCENT_BLUE, bg=BG_SECONDARY, anchor="w", cursor="hand2")
            lbl_url.pack(fill="x")
            lbl_url.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))
            
            # Right side Chevron indicator
            chevron_lbl = tk.Label(header_frame, text="▼", font=("Segoe UI", 12), fg=TEXT_MUTED, bg=BG_SECONDARY)
            chevron_lbl.pack(side="right", padx=15)
            
            # Content Frame (initially hidden)
            content_frame = tk.Frame(card, bg=BG_CONTAINER)
            
            # Expand / Collapse toggle function
            def toggle_card(event=None, cf=content_frame, chevron=chevron_lbl, card_frame=card):
                if cf.winfo_ismapped():
                    cf.pack_forget()
                    chevron.configure(text="▼")
                    card_frame.configure(bg=BG_SECONDARY)
                else:
                    cf.pack(fill="x", padx=15, pady=(0, 15))
                    chevron.configure(text="▲")
                    card_frame.configure(bg=BG_CONTAINER)
            
            # Bind click events on header to expand/collapse
            header_frame.bind("<Button-1>", toggle_card)
            lbl_title.bind("<Button-1>", toggle_card)
            
            # Hover effects
            def on_header_enter(e, hf=header_frame, ch=chevron_lbl):
                hf.configure(bg=BG_TERTIARY)
                ch.configure(fg=ACCENT_CYAN)
            def on_header_leave(e, hf=header_frame, ch=chevron_lbl):
                hf.configure(bg=BG_SECONDARY)
                ch.configure(fg=TEXT_MUTED)
                
            header_frame.bind("<Enter>", on_header_enter)
            header_frame.bind("<Leave>", on_header_leave)
            
            if err:
                tk.Label(content_frame, text=f"⚠️ Blocked / Scraping Error: {err}", font=("Segoe UI", 9, "italic"), fg=ACCENT_RED, bg=BG_CONTAINER, anchor="w", justify="left").pack(fill="x", pady=5)
            else:
                if description:
                    tk.Label(content_frame, text="📝 Page Description:", font=("Segoe UI", 9, "bold"), fg=ACCENT_PURPLE, bg=BG_CONTAINER, anchor="w").pack(fill="x", pady=(10, 2))
                    tk.Label(content_frame, text=description, font=("Segoe UI", 9), fg=TEXT_MAIN, bg=BG_CONTAINER, wraplength=700, justify="left", anchor="w").pack(fill="x", pady=(0, 8))
                
                tk.Label(content_frame, text="📋 Heading Outline:", font=("Segoe UI", 9, "bold"), fg=ACCENT_PURPLE, bg=BG_CONTAINER, anchor="w").pack(fill="x", pady=(5, 2))
                
                if headings:
                    for h in headings:
                        indent = 15 if h["tag"] == "h2" else 35
                        bullet = "• " if h["tag"] == "h2" else "◦ "
                        fg = ACCENT_BLUE if h["tag"] == "h2" else TEXT_MAIN
                        font_style = ("Segoe UI", 9, "bold") if h["tag"] == "h2" else ("Segoe UI", 9)
                        
                        tk.Label(content_frame, text=f"{bullet}{h['text']}", font=font_style, fg=fg, bg=BG_CONTAINER, anchor="w", wraplength=600, justify="left").pack(fill="x", padx=indent, pady=1)
                else:
                    h2_list = cc_i.get("h2", [])
                    h3_list = cc_i.get("h3", [])
                    if h2_list or h3_list:
                        for h2 in h2_list:
                            tk.Label(content_frame, text=f"• {h2}", font=("Segoe UI", 9, "bold"), fg=ACCENT_BLUE, bg=BG_CONTAINER, anchor="w", wraplength=650, justify="left").pack(fill="x", padx=15, pady=1)
                            for h3 in h3_list:
                                tk.Label(content_frame, text=f"   ◦ {h3}", font=("Segoe UI", 9), fg=TEXT_MAIN, bg=BG_CONTAINER, anchor="w", wraplength=650, justify="left").pack(fill="x", padx=30, pady=1)
                    else:
                        tk.Label(content_frame, text="No H2 or H3 outlines identified on this page.", font=("Segoe UI", 9, "italic"), fg=TEXT_MUTED, bg=BG_CONTAINER, anchor="w").pack(fill="x", pady=10)

        # 4. GAPS
        gaps = res.get("gaps", [])
        if gaps:
            for g_idx, gap in enumerate(gaps, 1):
                bk = tk.Frame(ca_sub_frames["gaps"], bg=BG_SECONDARY, highlightbackground=ACCENT_YELLOW, highlightthickness=1)
                bk.pack(fill="x", pady=3)
                tk.Label(bk, text=f"🕳️ Gap {g_idx}: {gap}", font=("Segoe UI", 9, "bold"), fg=TEXT_MAIN, bg=BG_SECONDARY, wraplength=700, anchor="w", justify="left").pack(fill="x", padx=15, pady=8)

        # 5. SUGGESTIONS
        sug = res.get("sug", [])
        if sug:
            for s_idx, s in enumerate(sug, 1):
                bk = tk.Frame(ca_sub_frames["sug"], bg="#0c4a6e", highlightbackground=ACCENT_BLUE, highlightthickness=1)
                bk.pack(fill="x", pady=3)
                tk.Label(bk, text=f"💡 Suggestion {s_idx}: {s}", font=("Segoe UI", 9, "bold"), fg=TEXT_MAIN, bg="#0c4a6e", wraplength=700, anchor="w", justify="left").pack(fill="x", padx=15, pady=8)

        switch_ca_sub_tab("serp")

    # --- PAGE 5: SETTINGS ---
    def build_settings_page(self):
        page = ttk.Frame(self.viewport, style='TFrame')
        
        # Header (static, non-scrollable)
        lbl_frame = ttk.Frame(page, style='TFrame')
        lbl_frame.pack(fill="x", padx=30, pady=(20, 10))
        ttk.Label(lbl_frame, text="SETTINGS", style='Header.TLabel').pack(anchor="w")
        ttk.Label(lbl_frame, text="Configure local API integrations and active search environment variables.", style='Subtitle.TLabel').pack(anchor="w", pady=(5, 0))

        # Create a container frame for canvas and scrollbar
        container = tk.Frame(page, bg=BG_PRIMARY)
        container.pack(fill="both", expand=True, padx=30, pady=5)
        
        canvas = tk.Canvas(container, bg=BG_PRIMARY, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        
        # Scrollable inner frame
        scroll_frame = tk.Frame(canvas, bg=BG_PRIMARY)
        
        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas_window = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        
        # Make the scroll frame stretch to the width of the canvas
        def configure_canvas_width(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", configure_canvas_width)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Mouse wheel binding for easy scrolling
        def on_mouse_wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        # Bind to canvas and all its children recursively on hover
        def bind_mouse_wheel(widget):
            widget.bind("<MouseWheel>", on_mouse_wheel)
            for child in widget.winfo_children():
                bind_mouse_wheel(child)
                
        scroll_frame.bind("<Enter>", lambda _: bind_mouse_wheel(scroll_frame))

        # Helper function to create section cards
        def create_section_card(parent, title, desc):
            card = tk.Frame(parent, bg=BG_SECONDARY, bd=0, highlightbackground=BG_BORDER, highlightthickness=1)
            card.pack(fill="x", pady=10, ipady=10)
            
            header = tk.Frame(card, bg=BG_SECONDARY, padx=25, pady=15)
            header.pack(fill="x")
            
            tk.Label(header, text=title, font=("Segoe UI", 12, "bold"), fg=ACCENT_CYAN, bg=BG_SECONDARY, anchor="w").pack(fill="x")
            if desc:
                tk.Label(header, text=desc, font=("Segoe UI", 9), fg=TEXT_MUTED, bg=BG_SECONDARY, anchor="w").pack(fill="x", pady=(2, 0))
                
            return card

        # Helper to add inputs to section cards
        def create_api_row(parent, label, description, var_name, placeholder):
            row = tk.Frame(parent, bg=BG_SECONDARY, padx=25, pady=8)
            row.pack(fill="x")
            
            tk.Label(row, text=label, font=("Segoe UI", 10, "bold"), fg=TEXT_MAIN, bg=BG_SECONDARY, anchor="w").pack(fill="x")
            if description:
                tk.Label(row, text=description, font=("Segoe UI", 8), fg=TEXT_MUTED, bg=BG_SECONDARY, anchor="w").pack(fill="x", pady=(2, 5))
                
            entry = CanvasEntry(row, placeholder=placeholder)
            entry.pack(fill="x", pady=2)
            
            # Prepopulate value
            val = os.getenv(var_name, "")
            if val:
                entry.entry.delete(0, tk.END)
                entry.entry.insert(0, val)
                entry.entry.configure(fg=TEXT_MAIN)
                
            return entry

        # -------------------------------------------------------------
        # CARD 1: Core AI & Search Engine APIs
        # -------------------------------------------------------------
        card_core = create_section_card(scroll_frame, "🤖 Core AI & Search Engines", "Configure your core content synthesis, search rankings, and keyword suggestion settings.")
        self.ent_settings_openai = create_api_row(card_core, "OpenAI API Key", "Required to draft the final markdown copy, answer custom user prompts, and extract main keyword ideas.", "OPENAI_API_KEY", "e.g., sk-proj-...")
        self.ent_settings_openai_base = create_api_row(card_core, "OpenAI API Base URL (Optional Proxy)", "Override standard OpenAI API endpoint (useful to bypass firewall or regional blocks).", "OPENAI_API_BASE", "e.g., https://api.openai-proxy.com/v1")
        self.ent_settings_serp = create_api_row(card_core, "SerpAPI Key", "Required to query live Google organic listings, shopping products, inline videos, and search autocompletes.", "SERP_API_KEY", "e.g., your_serp_api_key")
        self.ent_settings_dataforseo = create_api_row(card_core, "DataForSEO API Key", "Required for search volume analysis and related keywords suggestions.", "DATAFORSEO_API_KEY", "e.g., your_dataforseo_api_key")

        # -------------------------------------------------------------
        # CARD 2: Social Platforms & Video Research APIs
        # -------------------------------------------------------------
        card_social = create_section_card(scroll_frame, "📱 Social Platforms & Video Research", "Configure platform credentials to capture live discussions, public threads, and video metadata.")
        self.ent_settings_youtube = create_api_row(card_social, "YouTube API Key", "Used to crawl relevant YouTube search videos and descriptions.", "YOUTUBE_API_KEY", "e.g., AIzaSy...")
        self.ent_settings_reddit_id = create_api_row(card_social, "Reddit Client ID", "Required to scrape subreddit discussions and trending forum comments.", "REDDIT_CLIENT_ID", "e.g., your_reddit_client_id")
        self.ent_settings_reddit_secret = create_api_row(card_social, "Reddit Client Secret", "Required to authenticate with the Reddit API.", "REDDIT_CLIENT_SECRET", "e.g., your_reddit_client_secret")

        # -------------------------------------------------------------
        # CARD 3: Google Ads Keyword Planner (Optional)
        # -------------------------------------------------------------
        card_ads = create_section_card(scroll_frame, "📊 Google Ads Keyword Planner (Optional)", "Optional credentials for extracting deep keyword ideas and search competition volumes.")
        self.ent_settings_ads_dev = create_api_row(card_ads, "Developer Token", "Your Google Ads API developer token.", "GOOGLE_ADS_DEVELOPER_TOKEN", "e.g., vVoDZezi...")
        self.ent_settings_ads_cust = create_api_row(card_ads, "Customer ID", "Format: 123-456-7890 (no spaces or letters).", "GOOGLE_ADS_CUSTOMER_ID", "e.g., 1234567890")
        self.ent_settings_ads_login = create_api_row(card_ads, "Login Customer ID", "Required if managing account is different from the target account.", "GOOGLE_ADS_LOGIN_CUSTOMER_ID", "e.g., 3076632739")
        self.ent_settings_ads_client_id = create_api_row(card_ads, "OAuth2 Client ID", "Google Cloud OAuth2 credentials Client ID.", "GOOGLE_ADS_CLIENT_ID", "e.g., xxx.apps.googleusercontent.com")
        self.ent_settings_ads_client_secret = create_api_row(card_ads, "OAuth2 Client Secret", "Google Cloud OAuth2 credentials Client Secret.", "GOOGLE_ADS_CLIENT_SECRET", "e.g., client_secret")
        self.ent_settings_ads_refresh = create_api_row(card_ads, "OAuth2 Refresh Token", "Your generated offline refresh token.", "GOOGLE_ADS_REFRESH_TOKEN", "e.g., 1//04mux...")

        # Action Buttons Panel
        btn_panel = tk.Frame(scroll_frame, bg=BG_PRIMARY, pady=15)
        btn_panel.pack(fill="x")
        
        save_btn = self.create_modern_button(btn_panel, "💾 Save Settings & API Keys", self.save_settings, primary=True)
        save_btn.pack(side="left")

        # -------------------------------------------------------------
        # System Storage & Application Logs Panel
        # -------------------------------------------------------------
        logs_card = tk.Frame(scroll_frame, bg=BG_SECONDARY, bd=0, highlightbackground=BG_BORDER, highlightthickness=1)
        logs_card.pack(fill="both", expand=True, pady=(15, 20))

        logs_frame = tk.Frame(logs_card, bg=BG_SECONDARY, padx=25, pady=25)
        logs_frame.pack(fill="both", expand=True)

        tk.Label(logs_frame, text="📂 System Storage & Application Logs", font=("Segoe UI", 11, "bold"), fg=TEXT_MAIN, bg=BG_SECONDARY, anchor="w").pack(fill="x", pady=(0, 5))
        tk.Label(logs_frame, text="View active local AppData folders, manage data directories, and troubleshoot runtime logs.", font=("Segoe UI", 9), fg=TEXT_MUTED, bg=BG_SECONDARY, anchor="w").pack(fill="x", pady=(0, 10))

        # Path display grid
        path_grid = tk.Frame(logs_frame, bg=BG_SECONDARY)
        path_grid.pack(fill="x", pady=(5, 10))

        def make_path_row(parent, row_idx, label_text, path_val):
            lbl = tk.Label(parent, text=label_text, font=("Segoe UI", 9, "bold"), fg=TEXT_MUTED, bg=BG_SECONDARY, anchor="w", width=18)
            lbl.grid(row=row_idx, column=0, sticky="w", pady=4)
            
            val_entry = tk.Entry(parent, font=("Segoe UI", 9), fg=TEXT_MAIN, bg="#1c1835", bd=0, highlightthickness=1, highlightbackground=BG_BORDER)
            val_entry.insert(0, path_val)
            val_entry.configure(state="readonly")
            val_entry.grid(row=row_idx, column=1, sticky="ew", pady=4, padx=(10, 0))
            parent.grid_columnconfigure(1, weight=1)

        make_path_row(path_grid, 0, "App Directory:", ENV_DIR)
        make_path_row(path_grid, 1, "Log File Path:", APP_LOG_PATH)

        # Buttons Row
        btn_row = tk.Frame(logs_frame, bg=BG_SECONDARY)
        btn_row.pack(fill="x", pady=(10, 15))

        self.create_modern_button(btn_row, "📂 Open App Folder", self.open_app_directory).pack(side="left", padx=(0, 10))
        self.create_modern_button(btn_row, "📄 Open Log File", self.open_log_file).pack(side="left", padx=(0, 10))
        self.create_modern_button(btn_row, "🔄 Refresh Preview", self.refresh_log_preview).pack(side="left")

        # Embedded Monospace Terminal Preview
        terminal_lbl = tk.Label(logs_frame, text="Recent Log Output Preview (Last 30 lines):", font=("Segoe UI", 9, "bold"), fg=TEXT_MUTED, bg=BG_SECONDARY, anchor="w")
        terminal_lbl.pack(fill="x", pady=(5, 5))

        preview_container = tk.Frame(logs_frame, bg="#0c0a1a", bd=1, relief="solid", highlightbackground=BG_BORDER, highlightthickness=1)
        preview_container.pack(fill="both", expand=True)

        scrollbar_text = ttk.Scrollbar(preview_container)
        scrollbar_text.pack(side="right", fill="y")

        self.log_text = tk.Text(
            preview_container, height=6, font=("Consolas", 9),
            bg="#0c0a1a", fg=ACCENT_CYAN, insertbackground=TEXT_MAIN,
            bd=0, yscrollcommand=scrollbar_text.set
        )
        self.log_text.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        scrollbar_text.config(command=self.log_text.yview)
        self.log_text.configure(state="disabled")

        return page

    def save_settings(self):
        # Collect all inputs
        updates = {
            "OPENAI_API_KEY": self.ent_settings_openai.entry.get().strip(),
            "OPENAI_API_BASE": self.ent_settings_openai_base.entry.get().strip(),
            "SERP_API_KEY": self.ent_settings_serp.entry.get().strip(),
            "DATAFORSEO_API_KEY": self.ent_settings_dataforseo.entry.get().strip(),
            "YOUTUBE_API_KEY": self.ent_settings_youtube.entry.get().strip(),
            "REDDIT_CLIENT_ID": self.ent_settings_reddit_id.entry.get().strip(),
            "REDDIT_CLIENT_SECRET": self.ent_settings_reddit_secret.entry.get().strip(),
            "GOOGLE_ADS_DEVELOPER_TOKEN": self.ent_settings_ads_dev.entry.get().strip(),
            "GOOGLE_ADS_CUSTOMER_ID": self.ent_settings_ads_cust.entry.get().strip(),
            "GOOGLE_ADS_LOGIN_CUSTOMER_ID": self.ent_settings_ads_login.entry.get().strip(),
            "GOOGLE_ADS_CLIENT_ID": self.ent_settings_ads_client_id.entry.get().strip(),
            "GOOGLE_ADS_CLIENT_SECRET": self.ent_settings_ads_client_secret.entry.get().strip(),
            "GOOGLE_ADS_REFRESH_TOKEN": self.ent_settings_ads_refresh.entry.get().strip(),
        }
        
        # Clean placeholders
        for k, v in updates.items():
            placeholder = getattr(getattr(self, f"ent_settings_{k.lower().replace('google_ads_', 'ads_').replace('reddit_client_', 'reddit_')}", None), "placeholder", "")
            if v == placeholder:
                updates[k] = ""

        # Update environment variables in-process
        for k, v in updates.items():
            os.environ[k] = v

        # Read and modify .env in-place to preserve comments and formatting
        env_path = ENV_PATH
        lines = []
        seen_keys = set()
        
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line_strip = line.strip()
                        if "=" in line_strip and not line_strip.startswith("#"):
                            key_part, val_part = line_strip.split("=", 1)
                            key_part = key_part.strip()
                            if key_part in updates:
                                lines.append(f"{key_part}={updates[key_part]}\n")
                                seen_keys.add(key_part)
                            else:
                                lines.append(line)
                        else:
                            lines.append(line)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to read .env file: {e}")
                return
        
        # Append any updates that weren't seen in the existing .env
        for k, v in updates.items():
            if k not in seen_keys:
                lines.append(f"{k}={v}\n")
                
        try:
            os.makedirs(os.path.dirname(env_path), exist_ok=True)
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to write to .env file: {e}")
            return
            
        try:
            # Re-read dotenv
            load_dotenv(dotenv_path=ENV_PATH, override=True)
            # Clear Pydantic config cache so backend components pick it up
            from app.config import get_settings
            get_settings.cache_clear()
        except Exception as e:
            pass
            
        messagebox.showinfo("Success", "All settings and API keys updated successfully!")

    def open_app_directory(self):
        try:
            if os.path.exists(ENV_DIR):
                os.startfile(ENV_DIR)
            else:
                messagebox.showerror("Error", f"App directory does not exist: {ENV_DIR}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open directory: {e}")

    def open_log_file(self):
        try:
            if os.path.exists(APP_LOG_PATH):
                os.startfile(APP_LOG_PATH)
            else:
                messagebox.showerror("Error", f"Log file does not exist: {APP_LOG_PATH}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open log file: {e}")

    def refresh_log_preview(self):
        if not hasattr(self, "log_text") or not self.log_text.winfo_exists():
            return
        try:
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", tk.END)
            
            if os.path.exists(APP_LOG_PATH):
                with open(APP_LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                # Get last 30 lines
                last_lines = lines[-30:]
                log_content = "".join(last_lines)
                self.log_text.insert(tk.END, log_content)
                self.log_text.see(tk.END)  # Scroll to the end automatically
            else:
                self.log_text.insert(tk.END, "Log file app.log does not exist yet. Run operations to generate logs.")
        except Exception as e:
            self.log_text.insert(tk.END, f"Error reading log file: {e}")
        finally:
            self.log_text.configure(state="disabled")

if __name__ == "__main__":
    root = tk.Tk()
    app = ContentGeneratorApp(root)
    root.mainloop()
