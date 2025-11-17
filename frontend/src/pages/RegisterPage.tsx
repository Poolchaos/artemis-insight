import { useState, type FormEvent, type ChangeEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { EnvelopeIcon, LockClosedIcon, UserIcon } from '@heroicons/react/24/outline';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';
import Card, { CardContent, CardHeader } from '../components/ui/Card';
import { useAuthStore } from '../stores/auth.store';

const RegisterPage = () => {
  const navigate = useNavigate();
  const { register, isLoading, error: authError } = useAuthStore();

  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  const validateField = (name: string, value: string): string => {
    switch (name) {
      case 'name':
        return !value.trim() ? 'Name is required' : '';
      case 'email':
        if (!value) return 'Email is required';
        if (!/\S+@\S+\.\S+/.test(value)) return 'Email is invalid';
        return '';
      case 'password':
        if (!value) return 'Password is required';
        if (value.length < 8) return 'Password must be at least 8 characters';
        return '';
      case 'confirmPassword':
        return value !== formData.password ? 'Passwords do not match' : '';
      default:
        return '';
    }
  };

  const handleFieldChange = (e: ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));

    // Validate field if it has been touched
    if (touched[name]) {
      const error = validateField(name, value);
      setErrors(prev => ({ ...prev, [name]: error }));
    }

    // Also revalidate confirmPassword when password changes
    if (name === 'password' && touched.confirmPassword) {
      const confirmError = formData.confirmPassword !== value ? 'Passwords do not match' : '';
      setErrors(prev => ({ ...prev, confirmPassword: confirmError }));
    }
  };

  const handleFieldBlur = (name: string) => {
    setTouched(prev => ({ ...prev, [name]: true }));
    const error = validateField(name, formData[name as keyof typeof formData]);
    setErrors(prev => ({ ...prev, [name]: error }));
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    Object.keys(formData).forEach(key => {
      const error = validateField(key, formData[key as keyof typeof formData]);
      if (error) newErrors[key] = error;
    });

    setErrors(newErrors);
    setTouched({ name: true, email: true, password: true, confirmPassword: true });
    return Object.keys(newErrors).length === 0;
  };

  const getPasswordStrength = (password: string): { strength: string; color: string } => {
    if (!password) return { strength: '', color: '' };
    if (password.length < 6) return { strength: 'Weak', color: 'text-red-600 dark:text-red-400' };
    if (password.length < 10) return { strength: 'Medium', color: 'text-amber-600 dark:text-amber-400' };
    return { strength: 'Strong', color: 'text-green-600 dark:text-green-400' };
  };

  const passwordStrength = getPasswordStrength(formData.password);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    if (!validateForm()) return;

    try {
      await register(formData.email, formData.name, formData.password);
      navigate('/dashboard');
    } catch (error) {
      // Error is handled by the store
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo/Title */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">
            Artemis Insight
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            AI-powered document intelligence
          </p>
        </div>

        {/* Register Card */}
        <Card>
          <CardHeader>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              Create Account
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Sign up to get started with Artemis Insight
            </p>
          </CardHeader>

          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Global Error */}
              {authError && (
                <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                  <p className="text-sm text-red-600 dark:text-red-400">{authError}</p>
                </div>
              )}

              {/* Name Input */}
              <Input
                label="Full Name"
                type="text"
                name="name"
                placeholder="John Doe"
                value={formData.name}
                onChange={handleFieldChange}
                onBlur={() => handleFieldBlur('name')}
                error={errors.name}
                leftIcon={<UserIcon className="h-5 w-5" />}
                disabled={isLoading}
              />

              {/* Email Input */}
              <Input
                label="Email"
                type="email"
                name="email"
                placeholder="john@example.com"
                value={formData.email}
                onChange={handleFieldChange}
                onBlur={() => handleFieldBlur('email')}
                error={errors.email}
                leftIcon={<EnvelopeIcon className="h-5 w-5" />}
                disabled={isLoading}
              />

              {/* Password Input */}
              <div>
                <Input
                  label="Password"
                  type="password"
                  name="password"
                  placeholder="••••••••"
                  value={formData.password}
                  onChange={handleFieldChange}
                  onBlur={() => handleFieldBlur('password')}
                  error={errors.password}
                  leftIcon={<LockClosedIcon className="h-5 w-5" />}
                  disabled={isLoading}
                />
                {formData.password && passwordStrength.strength && (
                  <p className={`text-xs mt-1 ${passwordStrength.color}`}>
                    Password strength: {passwordStrength.strength}
                  </p>
                )}
              </div>

              {/* Confirm Password Input */}
              <Input
                label="Confirm Password"
                type="password"
                name="confirmPassword"
                placeholder="••••••••"
                value={formData.confirmPassword}
                onChange={handleFieldChange}
                onBlur={() => handleFieldBlur('confirmPassword')}
                error={errors.confirmPassword}
                leftIcon={<LockClosedIcon className="h-5 w-5" />}
                disabled={isLoading}
              />

              {/* Submit Button */}
              <Button
                type="submit"
                fullWidth
                isLoading={isLoading}
                disabled={isLoading}
              >
                {isLoading ? 'Creating account...' : 'Create Account'}
              </Button>

              {/* Login Link */}
              <p className="text-center text-sm text-gray-600 dark:text-gray-400">
                Already have an account?{' '}
                <Link
                  to="/login"
                  className="font-medium text-primary-600 hover:text-primary-500 dark:text-primary-400"
                >
                  Sign in
                </Link>
              </p>
            </form>
          </CardContent>
        </Card>

        {/* Footer */}
        <p className="text-center text-sm text-gray-500 dark:text-gray-400 mt-8">
          © 2025 Artemis Insight. All rights reserved.
        </p>
      </div>
    </div>
  );
};

export default RegisterPage;
