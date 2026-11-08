"""Build-time UI budgets. Never started by normal application use."""
import math
import statistics
import time


BUDGETS = {
    'ui_startup_ms': 2000,
    'navigation_median_ms': 100,
    'navigation_p95_ms': 500,
    'scroll_median_ms': 100,
    'scroll_p95_ms': 500,
    'idle_cpu_ratio': 0.10,
}


def _timings(samples):
    ordered = sorted(samples)
    return statistics.median(ordered), ordered[math.ceil(len(ordered) * 0.95) - 1]


def measure(app, startup_ms, rounds=3, idle_seconds=2):
    """Exercise synthetic UI only, preserving the selected tab and scroll positions."""
    root = app.root
    selected = app.notebook.select()
    positions = [(canvas, canvas.yview()[0]) for _, canvas in app.scroll_tabs]
    navigation, scrolling = [], []
    try:
        # Warm every page once, then measure repeated visits. Startup is reported
        # separately, so deferred first-use work does not disappear from evidence.
        for tab in app.notebook.tabs():
            app.notebook.select(tab)
            root.update()
        for _ in range(rounds):
            for tab in app.notebook.tabs():
                started = time.perf_counter()
                app.notebook.select(tab)
                root.update()
                navigation.append((time.perf_counter() - started) * 1000)
            for frame, canvas in app.scroll_tabs:
                app.notebook.select(canvas.master)
                root.update()
                for fraction in (0.5, 1.0, 0.0):
                    started = time.perf_counter()
                    canvas.yview_moveto(fraction)
                    root.update()
                    scrolling.append((time.perf_counter() - started) * 1000)
        app.notebook.select(0)
        root.update()
        started, cpu = time.perf_counter(), time.process_time()
        timer = root.after(round(idle_seconds * 1000), root.quit)
        try:
            root.mainloop()
        finally:
            root.after_cancel(timer)
        elapsed, used = time.perf_counter() - started, time.process_time() - cpu
        nav_median, nav_p95 = _timings(navigation)
        scroll_median, scroll_p95 = _timings(scrolling)
        return dict(ui_startup_ms=round(startup_ms, 3),
                    navigation_median_ms=round(nav_median, 3), navigation_p95_ms=round(nav_p95, 3),
                    scroll_median_ms=round(scroll_median, 3), scroll_p95_ms=round(scroll_p95, 3),
                    idle_cpu_ratio=used / elapsed, idle_cpu_seconds=used, idle_wall_seconds=elapsed,
                    navigation_samples=len(navigation), scroll_samples=len(scrolling))
    finally:
        for canvas, position in positions:
            canvas.yview_moveto(position)
        app.notebook.select(selected)
        root.update()


def violations(metrics):
    failures = []
    for key, limit in BUDGETS.items():
        value = metrics.get(key)
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            failures.append(key + ': missing or invalid measurement')
        elif value > limit:
            failures.append(f'{key}: {value:.3f} exceeds {limit}')
    return failures
