using System.Windows;
using System.IO;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using TwitchClipper.Desktop.Models;
using TwitchClipper.Desktop.Services;
using TwitchClipper.Desktop.ViewModels;

namespace TwitchClipper.Desktop;

public partial class App : Application
{
    private ServiceProvider? _serviceProvider;

    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        var configuration = new ConfigurationBuilder()
            .SetBasePath(AppContext.BaseDirectory)
            .AddJsonFile("appsettings.json", optional: false)
            .Build();

        var settings = configuration.GetSection("Frontend").Get<AppSettings>() ?? new AppSettings();
        var services = new ServiceCollection();
        services.AddSingleton(settings);

        services.AddLogging(logging =>
        {
            logging.AddDebug();
            var logPath = Path.Combine(AppContext.BaseDirectory, "logs", "frontend.log");
            logging.AddProvider(new FileLoggerProvider(logPath));
        });

        services.AddSingleton<IApiErrorMapper, ApiErrorMapper>();
        services.AddSingleton<INavigationService, NavigationService>();
        services.AddSingleton<IDialogService, DialogService>();
        services.AddSingleton<IPathOpener, PathOpener>();
        services.AddHttpClient<IApiClient, ApiClient>(client =>
        {
            client.BaseAddress = new Uri(settings.ApiBaseUrl);
            client.Timeout = TimeSpan.FromSeconds(15);
        });

        services.AddSingleton<DashboardViewModel>();
        services.AddSingleton<VodHighlightsFormViewModel>();
        services.AddSingleton<ClipMontageFormViewModel>();
        services.AddSingleton<JobsQueueViewModel>();
        services.AddSingleton<JobDetailViewModel>();
        services.AddSingleton<AppShellViewModel>();
        services.AddSingleton<MainWindow>();

        _serviceProvider = services.BuildServiceProvider();

        var mainWindow = _serviceProvider.GetRequiredService<MainWindow>();
        mainWindow.Show();
    }

    protected override void OnExit(ExitEventArgs e)
    {
        _serviceProvider?.Dispose();
        base.OnExit(e);
    }
}
