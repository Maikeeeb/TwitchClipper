using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;

namespace TwitchClipper.Desktop.ViewModels;

public abstract class ViewModelBase : INotifyPropertyChanged
{
    private readonly ObservableCollection<string> _validationErrors = [];

    public event PropertyChangedEventHandler? PropertyChanged;

    public ReadOnlyObservableCollection<string> ValidationErrors { get; }

    public bool HasValidationErrors => _validationErrors.Count > 0;

    protected ViewModelBase()
    {
        ValidationErrors = new ReadOnlyObservableCollection<string>(_validationErrors);
    }

    protected void SetValidationErrors(IEnumerable<string> errors)
    {
        _validationErrors.Clear();
        foreach (var error in errors)
        {
            _validationErrors.Add(error);
        }

        OnPropertyChanged(nameof(HasValidationErrors));
    }

    protected bool SetProperty<T>(ref T field, T value, [CallerMemberName] string? propertyName = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value))
        {
            return false;
        }

        field = value;
        OnPropertyChanged(propertyName);
        return true;
    }

    protected void OnPropertyChanged([CallerMemberName] string? propertyName = null)
    {
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
    }
}
