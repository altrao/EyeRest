from pystray import Icon

class Win32PystrayIcon(Icon):
	WM_LBUTTONDBLCLK = 0x0203

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		if 'on_double_click' in kwargs:
			self.on_double_click = kwargs['on_double_click']

	def _on_notify(self, wparam, lparam):
		super()._on_notify(wparam, lparam)

		if lparam == self.WM_LBUTTONDBLCLK:
			self.on_double_click(self, None)
