from django.contrib.auth.models import BaseUserManager


class GerenciadorUsuario(BaseUserManager):
	def create_user(self, username, email, password=None, **extra_fields):
		if not email:
			raise ValueError('O endereço de email deve ser fornecido')
		
		if not username:
			raise ValueError("O usuário deve conter um nome identificador.")
		
		email = self.normalize_email(email)
		user = self.model(username=username, email=email, **extra_fields)
		
		user.set_password(password)
		user.save(using=self._db)
		return user

	def create_superuser(self, username, email, password=None, **extra_fields):
		"""
		Cria e salva um superusuário com os detalhes fornecidos.
		"""
		extra_fields.setdefault('is_staff', True)
		extra_fields.setdefault('is_superuser', True)
		extra_fields.setdefault('is_admin', False)
		extra_fields.setdefault('is_gerente', False)
		extra_fields.setdefault('is_ouvidor', False)

		if extra_fields.get('is_staff') is not True:
			raise ValueError('O superusuário deve ter is_staff=True.')
		
		if extra_fields.get('is_superuser') is not True:
			raise ValueError('O superusuário deve ter is_superuser=True.')

		return self.create_user(username, email, password, **extra_fields)
