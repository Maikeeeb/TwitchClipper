using System.Windows;
using TwitchClipper.Desktop.ViewModels;

namespace TwitchClipper.Desktop;

public partial class MainWindow : Window
{
    private readonly AppShellViewModel _viewModel;

    public MainWindow(AppShellViewModel viewModel)
    {
        InitializeComponent();
        _viewModel = viewModel;
        DataContext = _viewModel;

        Loaded += async (_, _) => await _viewModel.StartupHydrationAsync();
    }
}
