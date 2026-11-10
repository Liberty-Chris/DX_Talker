"""Render policy checks use write counts rather than runner timing."""
import unittest
from unittest.mock import Mock
from dxtalker.rendering import RenderCache


class RenderTests(unittest.TestCase):
    def test_equal_values_do_not_repeat_tk_writes(self):
        cache=RenderCache();variable=Mock();button=Mock();canvas=Mock()
        for _ in range(50):
            cache.set(variable,'Idle')
            cache.configure(button,state='disabled')
            cache.coords(canvas,2,0,0,20,24)
        variable.set.assert_called_once_with('Idle')
        button.configure.assert_called_once_with(state='disabled')
        canvas.coords.assert_called_once_with(2,0,0,20,24)
        cache.set(variable,'Receiving');cache.configure(button,state='normal');cache.coords(canvas,2,0,0,40,24)
        self.assertEqual(variable.set.call_count,2)
        self.assertEqual(button.configure.call_count,2)
        self.assertEqual(canvas.coords.call_count,2)
