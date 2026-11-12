package EcoGrid.dao;

import EcoGrid.entity.Usuario;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface UsuarioRepository extends JpaRepository<Usuario, Long> {

    @EntityGraph(attributePaths = "idrol")
    List<Usuario> findByCifOrderByNombreAsc(String cif);

    @EntityGraph(attributePaths = "idrol")
    Optional<Usuario> findByIdAndCif(Long id, String cif);

    @EntityGraph(attributePaths = "idrol")
    Optional<Usuario> findByCifAndEmailIgnoreCase(String cif, String email);



    boolean existsByCifAndEmailIgnoreCase(String cif, String email);
}