using TwitchClipper.Desktop.Models;

namespace TwitchClipper.Desktop.Services;

public interface INavigationService
{
    AppScreen CurrentScreen { get; }

    event EventHandler<AppScreen>? ScreenChanged;

    void NavigateTo(AppScreen screen);
}

public sealed class NavigationService : INavigationService
{
    private AppScreen _currentScreen = AppScreen.Dashboard;

    public AppScreen CurrentScreen => _currentScreen;

    public event EventHandler<AppScreen>? ScreenChanged;

    public void NavigateTo(AppScreen screen)
    {
        if (_currentScreen == screen)
        {
            return;
        }

        _currentScreen = screen;
        ScreenChanged?.Invoke(this, screen);
    }
}
